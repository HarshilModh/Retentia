from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.db.session import init_db
from app.db.crud import upsert_concept
from app.vectorstore.store import get_subject_kb


# The curriculum. prereqs chains the concepts: chromosomes -> mitosis -> meiosis,
# matching how the seed_docs/ markdown content actually depends on itself.
SEED_CONCEPTS = [
    {"id": "chromosomes", "subject": "biology", "title": "Chromosomes",
     "summary": "Thread-like DNA structures in the nucleus.", "prereqs": [], "seq": 0},
    {"id": "mitosis", "subject": "biology", "title": "Mitosis",
     "summary": "Cell division producing two identical cells.", "prereqs": ["chromosomes"], "seq": 1},
    {"id": "meiosis", "subject": "biology", "title": "Meiosis",
     "summary": "Cell division producing four diverse gametes.", "prereqs": ["chromosomes", "mitosis"], "seq": 2},
]


# Called both by main() below (seeding) AND by the POST /ingest route
# (app/api/routes/ingest.py), so new documents can be added later without
# duplicating this logic.
def ingest_docs(docs: list[dict]):
    # chunk_size=1000: embedding models work best on paragraph-sized text,
    # not whole documents. chunk_overlap=150: the last 150 chars of one
    # chunk repeat at the start of the next, so a sentence that straddles
    # a cut point isn't lost from either chunk.
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    store = get_subject_kb()

    for doc in docs:
        upsert_concept(doc)  # saves title/summary/prereqs/seq to Postgres
        chunks = splitter.split_text(doc["content"])
        # concept_id here is what search_subject_kb(query, concept_id=...) later
        # filters on — this metadata is the link between Qdrant chunks and
        # the concepts table.
        store.add_texts(
            chunks,
            metadatas=[
                {"concept_id": doc["id"], "source": doc.get("source", doc["id"]), "chunk_index": i}
                for i in range(len(chunks))
            ],
        )


# Reads each seed_docs/*.md file (filename == concept id) and ingests it.
# Safe to re-run: upsert_concept and add_texts don't error on repeats,
# though re-running will duplicate chunks in Qdrant (no dedup logic yet).
def main():
    init_db()
    docs = []
    for concept in SEED_CONCEPTS:
        path = Path(__file__).parent / "seed_docs" / f"{concept['id']}.md"
        docs.append({**concept, "content": path.read_text(), "source": path.name})
    ingest_docs(docs)
    print(f"Ingested {len(docs)} docs into subject_kb")

if __name__ == "__main__":
    main()