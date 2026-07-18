from functools import lru_cache
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from app.config import QDRANT_URL, EMBED_DIM

@lru_cache(maxsize=1)
def _client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)

def ensure_collection(name: str):
    client = _client()
    if not client.collection_exists(name):
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )