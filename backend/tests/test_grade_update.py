from datetime import datetime, timedelta, timezone

import pytest

from app.config import BASE_FAIL_INTERVAL_DAYS
from app.core.learner import compute_grade_update

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def state(mastery=0.0, streak=0, misconceptions=None):
    return {
        "mastery": mastery,
        "streak": streak,
        "attempts": 0,
        "misconceptions": misconceptions if misconceptions is not None else [],
    }


def run(current, quality, misconception=None):
    return compute_grade_update(current, quality, misconception, NOW)


def test_first_pass():
    r = run(state(), 1.0)
    assert r["passed"] is True
    assert r["mastery"] == pytest.approx(0.4)
    assert r["streak"] == 1
    assert r["status"] == "learning"
    assert r["next_review"] == NOW + timedelta(days=1)


def test_streak_grows_and_interval_doubles():
    r = run(state(mastery=0.5, streak=2), 0.9)
    assert r["streak"] == 3
    assert r["next_review"] == NOW + timedelta(days=4)


def test_fail_resets_streak_and_schedules_short_review():
    r = run(state(mastery=0.8, streak=4), 0.2)
    assert r["passed"] is False
    assert r["streak"] == 0
    assert r["next_review"] == NOW + timedelta(days=BASE_FAIL_INTERVAL_DAYS)


def test_fail_is_due_sooner_than_first_pass():
    assert run(state(), 0.1)["next_review"] < run(state(), 0.9)["next_review"]


def test_quality_above_one_is_clamped():
    r = run(state(), 1.4)
    assert r["quality"] == 1.0
    assert r["mastery"] == pytest.approx(0.4)


def test_quality_below_zero_is_clamped():
    r = run(state(mastery=0.5), -0.2)
    assert r["quality"] == 0.0
    assert r["mastery"] == pytest.approx(0.3)


def test_score_on_the_line_passes():
    assert run(state(), 0.6)["passed"] is True


def test_score_just_under_the_line_fails():
    r = run(state(streak=3), 0.59)
    assert r["passed"] is False
    assert r["streak"] == 0


def test_becomes_mastered_at_threshold():
    r = run(state(mastery=0.9), 1.0)
    assert r["mastery"] == pytest.approx(0.94)
    assert r["status"] == "mastered"


def test_misconception_is_appended_once_at_the_end():
    r = run(state(misconceptions=["a"]), 0.2, "b")
    assert r["misconceptions"] == ["a", "b"]


def test_no_misconception_leaves_list_unchanged():
    r = run(state(misconceptions=["a"]), 0.9, None)
    assert r["misconceptions"] == ["a"]


def test_input_list_is_not_mutated():
    original = ["a"]
    run(state(misconceptions=original), 0.2, "b")
    assert original == ["a"]


def test_same_inputs_give_same_output():
    assert run(state(mastery=0.3, streak=1), 0.7, "x") == run(
        state(mastery=0.3, streak=1), 0.7, "x"
    )


# --- response time -----------------------------------------------------------

from app.core.learner import compute_response_ms, build_grade_prompt, build_grader_reference


def test_response_time_42_seconds():
    posed = (NOW - timedelta(seconds=42)).isoformat()
    assert compute_response_ms(posed, NOW) == 42_000


def test_response_time_missing_posing_time_is_none():
    assert compute_response_ms(None, NOW) is None


def test_response_time_never_negative():
    posed = (NOW + timedelta(seconds=5)).isoformat()
    assert compute_response_ms(posed, NOW) == 0


# --- grader prompt and reference --------------------------------------------

def test_prompt_includes_course_passages_when_given():
    p = build_grade_prompt("Mitosis", "Cell division.", "Q?", "my answer", "PASSAGE ONE")
    assert "PASSAGE ONE" in p
    assert "my answer" in p and "Cell division." in p


def test_prompt_falls_back_to_summary_when_no_passages():
    p = build_grade_prompt("Mitosis", "Cell division.", "Q?", "my answer", "")
    assert "Course material" not in p
    assert "Cell division." in p


def test_reference_is_joined_and_truncated():
    ref = build_grader_reference(["a" * 50, "b" * 50], max_chars=60)
    assert len(ref) == 60
    assert ref.startswith("a" * 50)


def test_reference_of_nothing_is_empty():
    assert build_grader_reference([]) == ""
    assert build_grader_reference(["", ""]) == ""
