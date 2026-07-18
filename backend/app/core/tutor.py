from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

from app.config import MAX_AGENT_STEPS, CHAT_HISTORY_LIMIT
from app.core.retrieval import search_subject_kb, recall_persona as _recall_persona, save_memory as _save_memory
from app.core.learner import apply_grade, select_next_concept as _select_next_concept, grade_answer
from app.db.crud import get_session, upsert_session, get_concept, get_all_learner_concepts

# Aliased imports (recall_persona -> _recall_persona, etc.) because the @tool
# functions below reuse those exact names. The tool wraps the underlying
# plain function; without the alias, the name would collide with itself.


# @tool turns a normal Python function into something the LLM can call.
# The docstring is NOT just documentation for us — it's what the LLM reads
# to decide WHEN to call this tool. Vague docstrings = agent picks wrong tools.
@tool
def search_kb(query: str, concept_id: str | None = None):
    """Search the subject knowledge base for curriculum content relevant to the query.
    Pass concept_id to restrict the search to one concept."""
    docs = search_subject_kb(query, concept_id=concept_id)
    return "\n\n".join(d.page_content for d in docs) or "No matching content found."


# RunnableConfig is how user_id gets into a tool WITHOUT the LLM supplying it.
# LangChain automatically hides the "config" parameter from the tool schema
# shown to the model — the LLM only ever sees "query" as an argument.
# We inject user_id ourselves when invoking the agent (see take_turn below),
# so there's no way for the model to hallucinate or spoof another user's id.
@tool
def recall_persona(query: str, config: RunnableConfig) -> str:
    """Recall what we know about this specific learner (preferences, past struggles) related to the query."""
    user_id = config["configurable"]["user_id"]
    docs = _recall_persona(user_id, query)
    return "\n".join(d.page_content for d in docs) or "No memories yet for this learner."


@tool
def save_memory(text: str, config: RunnableConfig) -> str:
    """Save a new observation about this learner for future personalization."""
    user_id = config["configurable"]["user_id"]
    _save_memory(user_id, text)
    return "Saved."


@tool
def get_learner_model(config: RunnableConfig) -> str:
    """Get this learner's current mastery, status, and streak for every concept."""
    user_id = config["configurable"]["user_id"]
    concepts = get_all_learner_concepts(user_id)
    lines = [f"{c['title']}: mastery={c['mastery']:.2f}, status={c['status']}, streak={c['streak']}" for c in concepts]
    return "\n".join(lines)


@tool
def pose_question(concept_id: str, question_text: str, config: RunnableConfig) -> str:
    """Ask the learner a question about a concept. Stores it as the pending question to grade next turn.
    concept_id MUST be an existing concept id (e.g. from get_learner_model or select_next_concept) —
    never invent one."""
    user_id = config["configurable"]["user_id"]
    # The LLM sometimes invents a concept_id that was never seeded (e.g. "meiosis_stages").
    # Validating here prevents grade_and_update from crashing later on a None concept.
    if not get_concept(concept_id):
        return (
            f"Error: '{concept_id}' is not a real concept id. Use one of the ids from "
            "get_learner_model or select_next_concept instead."
        )
    upsert_session(user_id, current_concept_id=concept_id, pending_question=question_text)
    return f"Question posed: {question_text}"


# The only tool that calls an LLM internally (via grade_answer -> structured
# output). Everything else here — the EMA math, streak/status update — is
# deterministic Python from learner.py, not something the agent's LLM decides.
@tool
def grade_and_update(answer: str, config: RunnableConfig) -> str:
    """Grade the learner's answer to the pending question and update their mastery."""
    user_id = config["configurable"]["user_id"]
    session = get_session(user_id)
    if not session or not session.get("pending_question"):
        return "No pending question to grade."

    concept_id = session["current_concept_id"]
    concept = get_concept(concept_id)
    if not concept:
        # Defensive fallback — should be unreachable now that pose_question validates
        # concept_id, but avoids a 500 if session state ever ends up inconsistent.
        upsert_session(user_id, current_concept_id=concept_id, pending_question=None)
        return f"Error: concept '{concept_id}' not found. Cleared the pending question — please pose a new one with a valid concept_id."
    grade = grade_answer(concept["title"], concept["summary"], session["pending_question"], answer)

    result = apply_grade(user_id, concept_id, grade.quality, grade.misconception)
    # Clear pending_question so the next turn doesn't re-grade the same answer.
    upsert_session(user_id, current_concept_id=concept_id, pending_question=None)

    return (
        f"Grade: {grade.quality:.2f}. {grade.explanation}\n"
        f"Mastery: {result['old_mastery']:.2f} -> {result['new_mastery']:.2f} "
        f"(status={result['status']}, streak={result['streak']}, next review in view)"
    )


@tool
def select_next_concept(config: RunnableConfig) -> str:
    """Pick what concept the learner should study next, based on due reviews, in-progress work, and unlocked prerequisites."""
    user_id = config["configurable"]["user_id"]
    concept = _select_next_concept(user_id)
    if not concept:
        return "No concept available — learner is caught up or has nothing unlocked."
    return f"Suggested next concept: {concept['title']} (id={concept['id']}, status={concept['status']})"

TOOLS=[search_kb, recall_persona, save_memory, get_learner_model, pose_question, grade_and_update, select_next_concept]


# Newer Gemini responses sometimes return AIMessage.content as a LIST of
# content blocks (e.g. [{"type": "text", "text": "...", "extras": {...}}])
# instead of a plain string. Discovered by actually running /chat live —
# the frontend's ChatResponse.answer is typed as a plain string, so this
# normalizes either shape into one before it ever leaves the backend.
def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return str(content)

# Lazy imports again — importing tutor.py (and therefore main.py) never
# requires a Gemini key. The key is only read when a real chat turn happens.
def build_agent():
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langgraph.prebuilt import create_react_agent
    from app.config import CHAT_MODEL, get_gemini_api_key

    llm = ChatGoogleGenerativeAI(model=CHAT_MODEL, google_api_key=get_gemini_api_key())
    # create_react_agent is the ONE line that builds the whole think -> act ->
    # observe loop: it wraps llm.bind_tools(TOOLS) and a LangGraph state
    # machine that keeps calling tools until the model decides to answer.
    return create_react_agent(llm, TOOLS)

SYSTEM_PROMPT = (
    "You are a personalized biology tutor. You have tools to search curriculum "
    "content, recall what you know about this learner, save new observations, "
    "check their mastery, pose questions, grade answers, and pick the next "
    "concept to study. Use tools as needed before answering.\n\n"
    "CRITICAL: Never type a question directly in your reply text. Every question "
    "you ask the learner MUST go through the pose_question tool — that is the "
    "ONLY way it gets tracked and graded. A question written in prose without "
    "calling pose_question will never be graded, and the learner's progress "
    "will not update.\n\n"
    "Likewise, when the learner answers a pending question, you MUST call "
    "grade_and_update BEFORE commenting on correctness. Never say \"correct\" "
    "or \"incorrect\" in your own words without calling grade_and_update first "
    "— only that tool computes the real mastery update. If grade_and_update "
    "returns \"No pending question to grade\", that means no question was "
    "properly recorded — call pose_question now to ask one properly instead "
    "of assuming the learner's answer was already judged."
)

def take_turn(user_id:str, message:str)->dict:
    # get_session returns None for a brand-new user with no session row yet —
    # fall back to {} so session.get(...) below never crashes on a first-ever chat.
    session=get_session(user_id) or {}
    agent=build_agent()

    system_text=SYSTEM_PROMPT
    if session.get("pending_question"):
          system_text += (
              f"\n\nThe learner has a pending question: '{session['pending_question']}'. "
              "Their next message is likely an answer to it — call grade_and_update."
          )

    # Replay recent chat history so the agent has multi-turn context.
    history = session.get("chat_history") or []
    messages = [SystemMessage(system_text)]
    for turn in history[-CHAT_HISTORY_LIMIT:]:
        cls = HumanMessage if turn["role"] == "user" else AIMessage
        messages.append(cls(turn["content"]))
    messages.append(HumanMessage(message))

    # {"messages": messages} is the actual input to the agent — this is what
    # was missing before. Without it, invoke() has nothing to reason over.
    # config carries user_id (read by every tool via RunnableConfig) and a
    # recursion_limit as a safety net so a confused agent can't loop forever.
    result = agent.invoke(
        {"messages": messages},
        config={
            "configurable": {"user_id": user_id},
            "recursion_limit": 2 * MAX_AGENT_STEPS + 1,
        },
    )
      
    result_messages = result["messages"]
    answer = _extract_text(result_messages[-1].content)
      
    tool_trace = []
    mastery_change = None
    suggestions = None
    for msg in result_messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            tool_trace += [call["name"] for call in msg.tool_calls]
        if isinstance(msg, ToolMessage):
            if msg.name == "grade_and_update":
                mastery_change = msg.content
            elif msg.name == "select_next_concept":
                suggestions = msg.content
                  
    # Re-fetch session AFTER the agent ran — tools like pose_question and
    # grade_and_update may have already changed current_concept_id /
    # pending_question mid-turn. If we blindly wrote back the OLD session
    # values here, we'd clobber what those tools just set.
    latest = get_session(user_id) or {}
    new_history = (history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": answer},
    ])[-CHAT_HISTORY_LIMIT:]

    upsert_session(
        user_id,
        chat_history=new_history,
        current_concept_id=latest.get("current_concept_id"),
        pending_question=latest.get("pending_question"),
    )   
  
    return {
        "answer": answer,
        "tool_trace": tool_trace,
        "mastery_change": mastery_change,
        "suggestions": suggestions,
    }

async def take_turn_stream(user_id: str, message: str):
      session = get_session(user_id) or {}
      agent = build_agent()
      
      system_text = SYSTEM_PROMPT
      if session.get("pending_question"):
          system_text += (
              f"\n\nThe learner has a pending question: '{session['pending_question']}'. "
              "Their next message is likely an answer to it — call grade_and_update."
          )   
  
      history = session.get("chat_history") or []
      messages = [SystemMessage(system_text)]
      for turn in history[-CHAT_HISTORY_LIMIT:]:
          cls = HumanMessage if turn["role"] == "user" else AIMessage
          messages.append(cls(turn["content"]))
      messages.append(HumanMessage(message))
      full_answer = ""
      tool_trace = []
      mastery_change = None
      suggestions = None
      
      async for event in agent.astream_events(
          {"messages": messages},
          version="v2",
          config={
              "configurable": {"user_id": user_id},
              "recursion_limit": 2 * MAX_AGENT_STEPS + 1,
          },
      ):  
          kind = event["event"]
          
          if kind == "on_chat_model_stream":
              token = _extract_text(event["data"]["chunk"].content)
              if token:
                  full_answer += token
                  yield {"type": "token", "content": token}
  
          elif kind == "on_tool_start":
              tool_trace.append(event["name"])
              yield {"type": "tool_call", "name": event["name"]}

          elif kind == "on_tool_end":
              name = event["name"]
              output = event["data"].get("output")
              content = getattr(output, "content", output)
              if name == "grade_and_update":
                  mastery_change = content
              elif name == "select_next_concept":
                  suggestions = content
              yield {"type": "tool_result", "name": name, "content": content}

      latest = get_session(user_id) or {}
      new_history = (history + [
          {"role": "user", "content": message},
          {"role": "assistant", "content": full_answer},
      ])[-CHAT_HISTORY_LIMIT:]

      upsert_session(
          user_id,
          chat_history=new_history,
          current_concept_id=latest.get("current_concept_id"),
          pending_question=latest.get("pending_question"),
      )
      
      yield {
          "type": "done",
          "tool_trace": tool_trace,
          "mastery_change": mastery_change,
          "suggestions": suggestions,
      }