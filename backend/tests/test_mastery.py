from app.core.learner import ema, compute_next_review


def test_ema_basic():
    assert ema(0, 1, 0.4) == 0.4


def test_ema_clamps_to_valid_range():
    assert ema(1.5, 1, 0.4) == 1.0
    assert ema(-0.5, 0, 0.4) == 0.0


def test_ema_converges_upward_with_repeated_perfect_scores():
    mastery = 0.0
    for _ in range(20):
        mastery = ema(mastery, 1.0, 0.4)
    assert mastery > 0.9


def test_ema_decays_downward_with_repeated_zero_scores():
    mastery = 1.0
    for _ in range(20):
        mastery = ema(mastery, 0.0, 0.4)
    assert mastery < 0.1


def test_compute_next_review_doubles_with_streak():
    assert compute_next_review(1) == 1
    assert compute_next_review(2) == 2
    assert compute_next_review(3) == 4
    assert compute_next_review(4) == 8


def test_compute_next_review_floors_at_base_interval():
    assert compute_next_review(0) == 1
