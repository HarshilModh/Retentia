from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import init_db
from app.vectorstore.client import ensure_collection
from app.config import SUBJECT_KB_COLLECTION, USER_BOX_COLLECTION

from app.api.routes import chat, progress, ingest


# lifespan replaces the deprecated @app.on_event("startup").
# Code before "yield" runs once when the server boots; code after "yield"
# would run on shutdown (nothing needed here).
# Notice: none of this needs a Gemini key — only Docker (Postgres + Qdrant)
# needs to be up. This is what lets "import app.main" succeed with no key set.
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()                                   # creates Postgres tables if missing
    ensure_collection(SUBJECT_KB_COLLECTION)    # creates Qdrant collection if missing
    ensure_collection(USER_BOX_COLLECTION)
    yield

app = FastAPI(lifespan=lifespan)

# CORS lets the frontend (running on a different port, e.g. localhost:5173)
# call this API. Without it, the browser blocks the request even though the
# server would respond fine.
# NOTE: allow_credentials=True together with allow_origins=["*"] is actually
# invalid per the CORS spec — browsers reject credentialed requests to a
# wildcard origin. Since we don't use cookies/auth yet, we skip credentials
# entirely. If auth is added later, allow_origins must become an explicit
# list (e.g. ["http://localhost:5173"]) instead of "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Each router was built independently in app/api/routes/ — this is the only
# place they get mounted onto the actual app, same idea as
# app.use('/api', router) in Express.
app.include_router(chat.router)
app.include_router(progress.router)
app.include_router(ingest.router)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
