from app.db.session import Base
from app.db import models  # noqa: F401 — import ensures models register on Base.metadata


def test_expected_tables_exist():
    table_names = set(Base.metadata.tables.keys())
    assert {"concepts", "learner_concept", "sessions"}.issubset(table_names)


def test_concepts_columns():
    columns = set(Base.metadata.tables["concepts"].columns.keys())
    assert {"id", "subject", "title", "summary", "prereqs", "seq"}.issubset(columns)


def test_learner_concept_composite_primary_key():
    table = Base.metadata.tables["learner_concept"]
    pk_columns = {col.name for col in table.primary_key.columns}
    assert pk_columns == {"user_id", "concept_id"}


def test_sessions_columns():
    columns = set(Base.metadata.tables["sessions"].columns.keys())
    assert {"user_id", "current_concept_id", "pending_question", "chat_history", "question_posed_at"}.issubset(columns)


def test_attempts_table_and_columns():
    assert "attempts" in Base.metadata.tables
    columns = set(Base.metadata.tables["attempts"].columns.keys())
    assert {
        "id", "user_id", "concept_id", "question", "answer", "quality", "passed",
        "misconception", "action_type", "hints_used", "response_ms", "created_at",
    } == columns


def test_attempts_index_on_user_concept_created():
    indexes = Base.metadata.tables["attempts"].indexes
    assert any([c.name for c in i.columns] == ["user_id", "concept_id", "created_at"] for i in indexes)
