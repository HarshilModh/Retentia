from sqlalchemy import and_
from sqlalchemy.dialects.postgresql import insert
from app.db.session import SessionLocal
from app.db.models import Concept, LearnerConcept, SessionState


# Insert a concept or update it if the same id already exists
def upsert_concept(concept: dict):
    # Build the INSERT statement with all column values
    stmt = insert(Concept).values(
        id=concept["id"],
        subject=concept.get("subject", ""),
        title=concept["title"],
        summary=concept.get("summary", ""),
        prereqs=concept.get("prereqs", []),
        seq=concept.get("seq", 0)
    )
    # on_conflict_do_update = PostgreSQL's "upsert" (INSERT ... ON CONFLICT DO UPDATE)
    # If a row with the same "id" already exists, instead of throwing an error,
    # PostgreSQL updates the existing row with the new values.
    # index_elements=["id"] tells it WHICH column to check for conflicts.
    # stmt.excluded refers to the NEW values that were just attempted to be inserted —
    # so stmt.excluded.subject means "use the new subject value from the failed insert"
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "subject": stmt.excluded.subject,
            "title": stmt.excluded.title,
            "summary": stmt.excluded.summary,
            "prereqs": stmt.excluded.prereqs,
            "seq": stmt.excluded.seq,
        }
    )
    # SessionLocal() creates a database session (like opening a connection).
    # "with" ensures the session is automatically closed when the block ends,
    # even if an error occurs — same idea as "with open(file)" in Python.
    with SessionLocal() as session:
        session.execute(stmt)   # runs the SQL
        session.commit()        # saves the changes permanently to the DB


# Fetch a single concept by its id
def get_concept(concept_id: str) -> dict | None:
    with SessionLocal() as session:
        row = session.get(Concept, concept_id)
        return _concept_to_dict(row) if row else None


# Fetch all concepts ordered by curriculum sequence
def get_concepts() -> list[dict]:
    with SessionLocal() as session:
        rows = session.query(Concept).order_by(Concept.seq).all()
        return [_concept_to_dict(r) for r in rows]


# Fetch one student's progress on one concept
def get_learner_concept(user_id: str, concept_id: str) -> dict | None:
    with SessionLocal() as session:
        row = session.get(LearnerConcept, (user_id, concept_id))
        return _learner_to_dict(row) if row else None


# Insert or update a student's progress on a concept
def upsert_learner_concept(user_id: str, concept_id: str, **fields):
    # **fields means this function accepts any extra keyword arguments
    # e.g. upsert_learner_concept("alice", "mitosis", mastery=0.6, streak=2)
    # Those extra args get packed into a dict called "fields"
    stmt = insert(LearnerConcept).values(
        user_id=user_id,
        concept_id=concept_id,
        **fields  # unpacks the dict as individual column=value pairs
    )
    # The composite primary key here is (user_id, concept_id) —
    # a conflict happens when BOTH match an existing row.
    # set_=fields means: on conflict, update only the columns that were passed in.
    # So if you only pass mastery=0.6, only mastery gets updated — nothing else changes.
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "concept_id"],
        set_=fields
    )
    with SessionLocal() as session:
        session.execute(stmt)
        session.commit()


# Fetch all concepts joined with this student's progress, filling defaults for untouched ones
def get_all_learner_concepts(user_id: str) -> list[dict]:
    with SessionLocal() as session:
        # outerjoin = LEFT JOIN in SQL.
        # Returns ALL concepts, and attaches the student's progress IF it exists.
        # If the student has never touched a concept, lc will be None for that row.
        # and_() lets us join on TWO conditions at once:
        #   1. concept id must match
        #   2. the learner row must belong to THIS user (not someone else)
        rows = session.query(Concept, LearnerConcept).outerjoin(
            LearnerConcept,
            and_(
                Concept.id == LearnerConcept.concept_id,
                LearnerConcept.user_id == user_id
            )
        ).order_by(Concept.seq).all()

        result = []
        for concept, lc in rows:
            d = _concept_to_dict(concept)
            if lc:
                d.update(_learner_to_dict(lc))
            else:
                d.update({
                    "mastery": 0.0,
                    "status": "not_started",
                    "attempts": 0,
                    "streak": 0,
                    "misconceptions": [],
                    "last_seen": None,
                    "next_review": None
                })
            result.append(d)
        return result


# Fetch a student's active session (current concept, pending question, chat history)
def get_session(user_id: str) -> dict | None:
    with SessionLocal() as session:
        row = session.get(SessionState, user_id)
        return _session_to_dict(row) if row else None


# Insert or update a student's active session
def upsert_session(user_id: str, **fields):
    stmt = insert(SessionState).values(
        user_id=user_id,
        **fields
    )
    # One session row per user (user_id is the primary key).
    # On conflict just update whatever fields were passed in.
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id"],
        set_=fields
    )
    with SessionLocal() as session:
        session.execute(stmt)
        session.commit()


# --- Helper functions: convert SQLAlchemy model objects to plain dicts ---

def _concept_to_dict(row: Concept) -> dict:
    return {
        "id": row.id,
        "subject": row.subject,
        "title": row.title,
        "summary": row.summary,
        "prereqs": row.prereqs or [],
        "seq": row.seq
    }


def _learner_to_dict(row: LearnerConcept) -> dict:
    return {
        "user_id": row.user_id,
        "concept_id": row.concept_id,
        "mastery": row.mastery,
        "status": row.status,
        "attempts": row.attempts,
        "streak": row.streak,
        "misconceptions": row.misconceptions or [],
        "last_seen": row.last_seen.isoformat() if row.last_seen else None,
        "next_review": row.next_review.isoformat() if row.next_review else None
    }


def _session_to_dict(row: SessionState) -> dict:
    return {
        "user_id": row.user_id,
        "current_concept_id": row.current_concept_id,
        "pending_question": row.pending_question,
        "chat_history": row.chat_history or []
    }
