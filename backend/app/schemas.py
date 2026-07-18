from pydantic import BaseModel, Field
from typing import Optional, List


# Structured output schema for LLM grading.
# We pass this to the LLM so it MUST return {quality, misconception, explanation}
# instead of free text — no JSON parsing needed on our side.
class Grade(BaseModel):
    quality: float = Field(..., description="Score 0.0-1.0. Above 0.6 means passed.")
    misconception: Optional[str] = Field(None, description="Describe the error if any. Null if correct.")
    explanation: str = Field(..., description="Feedback explaining the grade.")


# What the frontend sends to POST /chat.
# Note: no concept_id here — the backend tracks the current concept
# in the sessions table, the client never needs to send it.
class ChatRequest(BaseModel):
    user_id: str = Field(..., description="Unique student ID")
    message: str = Field(..., description="Message from the student")


# One document sent to POST /ingest
class IngestDoc(BaseModel):
    id: str
    subject: str
    title: str
    summary: Optional[str] = ""
    content: str
    prereqs: List[str] = Field(default_factory=list)
    seq: int = 0


# Bulk ingestion payload
class IngestRequest(BaseModel):
    docs: List[IngestDoc]
