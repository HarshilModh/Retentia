from datetime import datetime, timedelta, timezone
from app.config import (
    MASTERY_ALPHA,
    MASTERY_THRESHOLD,
    BASE_REVIEW_INTERVAL_DAYS,
    BASE_FAIL_INTERVAL_DAYS,
    PASS_THRESHOLD,
    GRADER_CONTEXT_CHARS,
)
from app.db.crud import get_learner_concept, save_graded_attempt, get_all_learner_concepts


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


# The grading calculation, with no database and no clock of its own: the
# current state, the quality score and "now" go in; the new state comes out.
# Same inputs always give the same output, so tests (and later the student
# simulator) can call it directly. apply_grade() below is the thin wrapper
# that reads the stored state, calls this, and saves the result.
def compute_grade_update(
    current: dict,
    quality: float,
    misconception: str | None,
    now: datetime,
    pass_threshold: float = PASS_THRESHOLD,
) -> dict:
    # Clamp first: ema() only clamps its output, so an out-of-range quality
    # (e.g. 1.4 from the grader) would otherwise inflate mastery and pass.
    quality = max(0.0, min(1.0, quality))

    passed = quality >= pass_threshold
    new_mastery = ema(current["mastery"], quality)
    new_streak = current["streak"] + 1 if passed else 0
    # Passing extends the review interval (SM-2); failing brings the concept
    # back soon, much sooner than even a first pass would.
    days = compute_next_review(new_streak) if passed else BASE_FAIL_INTERVAL_DAYS

    # Build a new list; never change the caller's list in place.
    misconceptions = list(current.get("misconceptions") or [])
    if misconception:
        misconceptions.append(misconception)

    return {
        "quality": quality,
        "passed": passed,
        "mastery": new_mastery,
        "status": "mastered" if new_mastery >= MASTERY_THRESHOLD else "learning",
        "streak": new_streak,
        "misconceptions": misconceptions,
        "next_review": now + timedelta(days=days),
    }


# How long the student took to answer, in milliseconds, measured from when the
# question was posed to "now". Returns None when the posing time is unknown
# (e.g. the question was posed before this was tracked), so grading never
# fails just because of a missing timestamp.
def compute_response_ms(posed_at_iso: str | None, now: datetime) -> int | None:
    if not posed_at_iso:
        return None
    posed_at = datetime.fromisoformat(posed_at_iso)
    return max(0, int((now - posed_at).total_seconds() * 1000))


# The main write-back function: called after a student answers a question.
# quality (0.0-1.0) comes from grade_answer() below.
# This is the ONLY place mastery, streak, and next_review get updated.
# The math itself lives in compute_grade_update() (pure, tested); this wrapper
# only reads the stored state, calls it, and saves the result together with an
# attempt-log row in one transaction (see crud.save_graded_attempt).
# question/answer are what was asked and the student's own words, stored in
# the attempt log. response_ms / hints_used / action_type are optional extras.
def apply_grade(
    user_id: str,
    concept_id: str,
    quality: float,
    misconception: str | None = None,
    *,
    question: str,
    answer: str,
    response_ms: int | None = None,
    hints_used: int = 0,
    action_type: str | None = None,
) -> dict:
    # If the student has never touched this concept before, start from defaults
    # instead of crashing on a missing row.
    current = get_learner_concept(user_id, concept_id) or {
        "mastery": 0.0, "attempts": 0, "streak": 0, "misconceptions": []
    }
    now = datetime.now(timezone.utc)
    update = compute_grade_update(current, quality, misconception, now)

    save_graded_attempt(
        user_id, concept_id,
        progress_fields=dict(
            mastery=update["mastery"],
            status=update["status"],
            attempts=current["attempts"] + 1,
            streak=update["streak"],
            misconceptions=update["misconceptions"],
            last_seen=now,
            next_review=update["next_review"],
        ),
        attempt_fields=dict(
            question=question,
            answer=answer,
            quality=update["quality"],
            passed=update["passed"],
            misconception=misconception,
            action_type=action_type,
            hints_used=hints_used,
            response_ms=response_ms,
        ),
    )

    # Returned as a plain dict so the agent tool (in tutor.py) can hand this
    # straight back to the LLM as a tool result, no extra conversion needed.
    return {
        "quality": update["quality"],
        "old_mastery": current["mastery"],
        "new_mastery": update["mastery"],
        "status": update["status"],
        "streak": update["streak"],
        "next_review": update["next_review"].isoformat(),
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


# Join retrieved course passages into one block for the grader, cutting it off
# at max_chars so the prompt (and token use) stays bounded. Empty in, empty out.
def build_grader_reference(passages: list[str], max_chars: int = GRADER_CONTEXT_CHARS) -> str:
    return "\n\n".join(p for p in passages if p)[:max_chars]


# The grader prompt, kept separate from the LLM call so it can be tested.
# reference (course content) is optional: with none, the grader works from the
# concept summary alone, exactly as before.
def build_grade_prompt(title: str, summary: str, question: str, answer: str, reference: str = "") -> str:
    prompt = (
        f"You are grading a student's answer about '{title}'.\n"
        f"Concept summary: {summary}\n"
    )
    if reference:
        prompt += f"Course material for this concept:\n{reference}\n"
    prompt += (
        f"Question: {question}\n"
        f"Student's answer: {answer}\n"
        "Grade the answer's quality and note any misconception."
    )
    return prompt


# The ONE LLM call in this file — everything else above is pure math.
# Imports are placed INSIDE the function (lazy pattern, same as vectorstore.py):
# ChatGoogleGenerativeAI and get_gemini_api_key() are only touched when this
# function actually runs, so importing learner.py never requires an API key
# and never fails just because Gemini isn't configured yet.
def grade_answer(title: str, summary: str, question: str, answer: str, reference: str = ""):
    from langchain_google_genai import ChatGoogleGenerativeAI
    from app.config import CHAT_MODEL, get_gemini_api_key
    from app.schemas import Grade

    llm = ChatGoogleGenerativeAI(model=CHAT_MODEL, google_api_key=get_gemini_api_key())
    # with_structured_output(Grade) forces the LLM's response into the exact
    # shape of the Grade pydantic model (quality, misconception, explanation).
    # No manual JSON parsing, no risk of the model replying in free text —
    # LangChain handles the schema enforcement under the hood.
    structured_llm = llm.with_structured_output(Grade)

    prompt = build_grade_prompt(title, summary, question, answer, reference)
    return structured_llm.invoke(prompt)
