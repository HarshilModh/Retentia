"""Tests for the grade_and_update agent tool with every outside dependency stubbed:
no database, no Qdrant, no LLM."""
from types import SimpleNamespace

import pytest

from app.core import tutor

CONFIG = {"configurable": {"user_id": "u1", "user_message": "its when the cell splits in two"}}


@pytest.fixture
def stubs(monkeypatch):
    """Stub everything the tool touches and record what it did."""
    calls = SimpleNamespace(graded=None, applied=None, sessions=[])
    session = {
        "current_concept_id": "mitosis",
        "pending_question": "What is mitosis?",
        "question_posed_at": None,
    }
    monkeypatch.setattr(tutor, "get_session", lambda uid: session)
    monkeypatch.setattr(tutor, "get_concept", lambda cid: {"id": cid, "title": "Mitosis", "summary": "Cell division."})
    monkeypatch.setattr(tutor, "search_subject_kb", lambda q, concept_id=None: [SimpleNamespace(page_content="PASSAGE")])
    monkeypatch.setattr(tutor, "upsert_session", lambda uid, **f: calls.sessions.append(f))

    def fake_grade(title, summary, question, answer, reference=""):
        calls.graded = dict(answer=answer, reference=reference)
        return SimpleNamespace(quality=0.8, misconception=None, explanation="Good.")

    def fake_apply(uid, cid, quality, misconception, **kw):
        calls.applied = dict(quality=quality, **kw)
        return {"quality": quality, "old_mastery": 0.0, "new_mastery": 0.32, "status": "learning", "streak": 1}

    monkeypatch.setattr(tutor, "grade_answer", fake_grade)
    monkeypatch.setattr(tutor, "apply_grade", fake_apply)
    return calls


def test_tool_takes_no_answer_argument():
    assert "answer" not in tutor.grade_and_update.args


def test_grades_the_students_exact_message(stubs):
    tutor.grade_and_update.invoke({}, config=CONFIG)
    assert stubs.graded["answer"] == "its when the cell splits in two"
    assert stubs.applied["answer"] == "its when the cell splits in two"
    assert stubs.applied["question"] == "What is mitosis?"


def test_grader_receives_course_passages(stubs):
    tutor.grade_and_update.invoke({}, config=CONFIG)
    assert stubs.graded["reference"] == "PASSAGE"


def test_pending_question_cleared_after_success(stubs):
    tutor.grade_and_update.invoke({}, config=CONFIG)
    assert stubs.sessions[-1]["pending_question"] is None


def test_grader_failure_writes_nothing_and_keeps_question_pending(stubs, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("quota exceeded")

    monkeypatch.setattr(tutor, "grade_answer", boom)
    out = tutor.grade_and_update.invoke({}, config=CONFIG)
    assert "grading failed" in out
    assert stubs.applied is None          # no attempt row, no mastery change
    assert stubs.sessions == []           # session untouched: question still pending


def test_no_pending_question_changes_nothing(stubs, monkeypatch):
    monkeypatch.setattr(tutor, "get_session", lambda uid: {"pending_question": None})
    out = tutor.grade_and_update.invoke({}, config=CONFIG)
    assert out == "No pending question to grade."
    assert stubs.applied is None
