from functools import lru_cache
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from app.config import (
    EMBED_MODEL,
    SUBJECT_KB_COLLECTION,
    USER_BOX_COLLECTION,
    get_gemini_api_key,
)
from app.vectorstore.client import _client, ensure_collection


# Lazily builds the embedding model on first use.
# This is where the API key is finally read — never at import time.
@lru_cache(maxsize=1)
def _embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(model=EMBED_MODEL, google_api_key=get_gemini_api_key())


# One cached store PER collection name (lru_cache keys on the argument).
# maxsize=None so both "subjects_kb" and "user_box" stay cached —
# maxsize=1 would evict one whenever the other is requested.
@lru_cache(maxsize=None)
def _store(name: str) -> QdrantVectorStore:
    ensure_collection(name)
    return QdrantVectorStore(
        client=_client(),
        collection_name=name,
        embedding=_embeddings(),
    )


def get_subject_kb() -> QdrantVectorStore:
    return _store(SUBJECT_KB_COLLECTION)


def get_user_box() -> QdrantVectorStore:
    return _store(USER_BOX_COLLECTION)
