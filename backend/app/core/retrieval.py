from qdrant_client.models import Filter, FieldCondition, MatchValue
from app.config import RETRIEVAL_K, PERSONA_K
from app.vectorstore.store import get_subject_kb, get_user_box


# Builds a Qdrant filter that matches one metadata field exactly.
# GOTCHA: langchain-qdrant stores our metadata nested under a "metadata" key
# in the Qdrant payload — so we must filter on "metadata.concept_id",
# not "concept_id". Filtering on the bare key silently matches nothing.
def _metaData_Filter(key: str, value: str):
    return Filter(must=[FieldCondition(key=f"metadata.{key}", match=MatchValue(value=value))])



# Search the shared textbook (subject_kb) — "WHAT to teach".
# If concept_id is given, only chunks from that concept are searched;
# otherwise the whole knowledge base.
def search_subject_kb(query: str, concept_id: str | None = None, k: int = RETRIEVAL_K):
    store = get_subject_kb()
    flt = _metaData_Filter("concept_id", concept_id) if concept_id else None
    return store.similarity_search(query, k=k, filter=flt)


# Search this learner's private memories (user_box) — "HOW to teach this person".
# ALWAYS filtered by user_id so one student's memories never leak into
# another student's session, even though all users share one collection.
def recall_persona(user_id: str, query: str, k: int = PERSONA_K):
    return get_user_box().similarity_search(query, k=k, filter=_metaData_Filter("user_id", user_id))


# Store a new memory about this learner (e.g. "prefers sports analogies").
# The text gets embedded and saved with user_id metadata for later filtering.
# Optional extra metadata is merged in alongside user_id.
def save_memory(user_id: str, text: str, meta: dict | None = None):
    return get_user_box().add_texts(texts=[text], metadatas=[{"user_id": user_id, **(meta or {})}])
