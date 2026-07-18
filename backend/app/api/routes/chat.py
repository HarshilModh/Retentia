from fastapi import APIRouter
from app.schemas import ChatRequest
from app.core.tutor import take_turn
import json
from fastapi.responses import StreamingResponse
from app.core.tutor import take_turn_stream
from app.db.crud import get_session

router = APIRouter()


# FastAPI validates the incoming JSON body against ChatRequest automatically —
# if user_id or message is missing/wrong-typed, the client gets a 422 error
# before this function even runs. take_turn() does ALL the real work
# (agent loop, tool calls, chat history); this route is just plumbing.
@router.post("/chat")
def chat(req: ChatRequest):
    return take_turn(req.user_id, req.message)
@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    async def event_generator():
        async for event in take_turn_stream(req.user_id, req.message):
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(event_generator(),media_type="text/event-stream")


# Lets the frontend restore the conversation on page load/refresh. The agent
# already had this memory server-side (take_turn replays chat_history into
# every turn) — this route just exposes it for the UI to display too.
@router.get("/chat/history/{user_id}")
def chat_history(user_id: str):
    session = get_session(user_id) or {}
    return {"chat_history": session.get("chat_history") or []}