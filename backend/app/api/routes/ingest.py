from fastapi import APIRouter
from app.schemas import IngestRequest
from ingest import ingest_docs   # reuses the exact same function the seed script uses

router = APIRouter()


# Lets new curriculum content be added later without restarting the server
# or touching seed_docs/. req.docs is a list of IngestDoc (validated by
# pydantic); model_dump() converts each one back into a plain dict because
# ingest_docs() expects dicts, not pydantic model instances.
@router.post("/ingest")
async def ingest_concepts(req: IngestRequest):
    docs = [doc.model_dump() for doc in req.docs]
    ingest_docs(docs)
    return {"ingested": len(docs)}