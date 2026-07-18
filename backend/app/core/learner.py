from datetime import datetime, timedelta, timezone
from app.config import MASTERY_ALPHA, MASTERY_THRESHOLD, BASE_REVIEW_INTERVAL_DAYS
from app.db.crud import get_learner_concept, upsert_learner_concept, get_all_learner_concepts


# EMA = Exponential Moving Average.
# Instead of overwriting mastery with the latest quiz score, we blend it with
# the old score. This smooths out noise — one lucky guess or one bad day
# doesn't swing mastery wildly, it just nudges it.
# alpha controls how much weight the NEW result gets (0.4 = 40% new, 60% history).
# The max/min clamp keeps the result inside the valid [0.0, 1.0] range no
# matter what old/quality/alpha are — protects every caller downstream.
def ema(old:float,quality:float,alpha:float=MASTERY_ALPHA)->float:
    new = (1 - alpha) * old + alpha * quality
    return max(0.0, min(1.0, new))


# SM-2-lite spaced repetition (same idea behind Anki flashcards):
# the longer your current correct-answer streak, the longer you can wait
# before reviewing this concept again — it's more solidly memorized.
# streak=1 -> 1 day, streak=2 -> 2 days, streak=3 -> 4 days, streak=4 -> 8 days...
# doubling each time streak grows by 1 (this is what "2 ** (streak-1)" does).
# max(1, streak) floors streak at 1 so streak=0 still returns the base interval
# instead of computing 2 ** -1 (which would be a fraction, not a whole day count).
def compute_next_review(streak: int) -> int:
    streak=max(1,streak)
    return BASE_REVIEW_INTERVAL_DAYS * (2 ** (streak - 1))


# The main write-back function: called after a student answers a question.
# quality (0.0-1.0) comes from grade_answer() below.
# This is the ONLY place mastery, streak, and next_review get updated —
# keeping all that logic in one deterministic function (not the LLM) means
# the same inputs always produce the same outputs, which is testable and
# doesn't hallucinate.
def apply_grade(user_id: str, concept_id: str, quality: float, misconception: str | None = None) -> dict:
    # If the student has never touched this concept before, start from defaults
    # instead of crashing on a missing row.
    current = get_learner_concept(user_id, concept_id) or {
        "mastery": 0.0, "attempts": 0, "streak": 0, "misconceptions": []
    }

    old_mastery = current["mastery"]
    new_mastery = ema(old_mastery, quality)

    # 0.6 is the pass/fail line: at or above it counts as a correct understanding.
    passed = quality >= 0.6
    new_streak = current["streak"] + 1 if passed else 0
    # Passing extends the review interval (SM-2); failing resets to a near-term
    # review so the student sees this concept again very soon.
    days = compute_next_review(new_streak) if passed else BASE_REVIEW_INTERVAL_DAYS

    # Misconceptions accumulate over time — every wrong-answer explanation
    # gets appended, building a history of this student's specific confusions.
    misconceptions = current["misconceptions"] or []
    if misconception:
        misconceptions = misconceptions + [misconception]

    status = "mastered" if new_mastery >= MASTERY_THRESHOLD else "learning"
    next_review = datetime.now(timezone.utc) + timedelta(days=days)

    # Persist everything in one upsert — this is the only place in the whole
    # app that writes to learner_concept after a grading event.
    upsert_learner_concept(
        user_id, concept_id,
        mastery=new_mastery,
        status=status,
        attempts=current["attempts"] + 1,
        streak=new_streak,
        misconceptions=misconceptions,
        last_seen=datetime.now(timezone.utc),
        next_review=next_review,
    )

    # Returned as a plain dict so the agent tool (in tutor.py) can hand this
    # straight back to the LLM as a tool result, no extra conversion needed.
    return {
        "old_mastery": old_mastery,
        "new_mastery": new_mastery,
        "status": status,
        "streak": new_streak,
        "next_review": next_review.isoformat(),
    }


# Decides what the student should study next. This is a PRIORITY CASCADE —
# each tier is checked in order, and we return as soon as one has candidates.
# The LLM never makes this decision; it just calls this tool and gets an answer.
def select_next_concept(user_id: str) -> dict | None:
    concepts = get_all_learner_concepts(user_id)
    now = datetime.now(timezone.utc)

    # Priority 1: due reviews (already started, and next_review has passed).
    # Spaced repetition demands these come first — if we don't review on
    # schedule, the whole SM-2 mechanism is pointless.
    due = [
        c for c in concepts
        if c["status"] != "not_started" and c["next_review"]
        and datetime.fromisoformat(c["next_review"]) <= now
    ]
    if due:
        # Of all overdue concepts, tackle the MOST overdue one first.
        return min(due, key=lambda c: datetime.fromisoformat(c["next_review"]))

    # Priority 2: in-progress, lowest mastery first — shore up the weakest
    # concept the student is currently learning before starting something new.
    in_progress = [c for c in concepts if c["status"] == "learning"]
    if in_progress:
        return min(in_progress, key=lambda c: c["mastery"])

    # Priority 3: not-started, but only concepts whose prerequisites are ALL
    # mastered — this enforces the curriculum's dependency order
    # (e.g. can't unlock "meiosis" until "mitosis" is mastered).
    # set(...).issubset(...) checks every prereq id is present in mastered_ids.
    mastered_ids = {c["id"] for c in concepts if c["status"] == "mastered"}
    not_started = [
        c for c in concepts
        if c["status"] == "not_started" and set(c["prereqs"]).issubset(mastered_ids)
    ]
    if not_started:
        # Among unlocked-but-untouched concepts, follow curriculum order (seq).
        return min(not_started, key=lambda c: c["seq"])

    # Nothing due, nothing in progress, nothing unlocked — student is caught up.
    return None


# The ONE LLM call in this file — everything else above is pure math.
# Imports are placed INSIDE the function (lazy pattern, same as vectorstore.py):
# ChatGoogleGenerativeAI and get_gemini_api_key() are only touched when this
# function actually runs, so importing learner.py never requires an API key
# and never fails just because Gemini isn't configured yet.
def grade_answer(title: str, summary: str, question: str, answer: str):
    from langchain_google_genai import ChatGoogleGenerativeAI
    from app.config import CHAT_MODEL, get_gemini_api_key
    from app.schemas import Grade

    llm = ChatGoogleGenerativeAI(model=CHAT_MODEL, google_api_key=get_gemini_api_key())
    # with_structured_output(Grade) forces the LLM's response into the exact
    # shape of the Grade pydantic model (quality, misconception, explanation).
    # No manual JSON parsing, no risk of the model replying in free text —
    # LangChain handles the schema enforcement under the hood.
    structured_llm = llm.with_structured_output(Grade)

    prompt = (
        f"You are grading a student's answer about '{title}'.\n"
        f"Concept summary: {summary}\n"
        f"Question: {question}\n"
        f"Student's answer: {answer}\n"
        "Grade the answer's quality and note any misconception."
    )
    return structured_llm.invoke(prompt)
