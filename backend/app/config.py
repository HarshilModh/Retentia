import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://userbox:userbox@localhost:5433/userbox")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

# Active: Gemini (comment this block out when switching to OpenAI)
# NOTE: both gemini-1.5-flash and text-embedding-004 are retired on the
# current Gemini API. gemini-embedding-001 replaces text-embedding-004 but
# outputs 3072-dim (not 768), so EMBED_DIM must match or Qdrant collection
# creation will silently create the wrong vector size and every similarity
# search will fail with a dimension mismatch.
# gemini-2.5-flash's free tier is only 20 requests/DAY — an agent turn burns
# 2-4+ calls internally (reasoning + each tool round-trip), so this gets
# exhausted almost immediately during dev. gemini-flash-lite-latest has a
# separate, much higher free-tier quota bucket — use it while developing.
CHAT_MODEL = os.getenv("CHAT_MODEL", "gemini-flash-lite-latest")
EMBED_MODEL = os.getenv("EMBED_MODEL", "models/gemini-embedding-001")
EMBED_DIM = 3072

# OpenAI (uncomment when you have credits)
# CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
# EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
# EMBED_DIM = 1536

SUBJECT_KB_COLLECTION="subjects_kb"
USER_BOX_COLLECTION="user_box"

RETRIEVAL_K=5
PERSONA_K=3
MAX_AGENT_STEPS = 10
CHAT_HISTORY_LIMIT=10

MASTERY_ALPHA = 0.4
MASTERY_THRESHOLD = 0.7
BASE_REVIEW_INTERVAL_DAYS = 1

# def get_openai_api_key() -> str:
#     key = os.getenv("OPENAI_API_KEY")
#     if not key:
#         raise RuntimeError("OPENAI_API_KEY is not set")
#     return key

def get_gemini_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    return key

