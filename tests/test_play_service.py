import math

from src.services.play_service import PlayService


def test_calculate_to_win_for_positive_odds():
    service = PlayService()
    assert math.isclose(service.calculate_to_win(10, 150), 15.0, rel_tol=1e-9)


def test_calculate_to_win_for_negative_odds():
    service = PlayService()
    assert math.isclose(service.calculate_to_win(10, -110), 9.09, rel_tol=1e-9)


def test_validate_play_rejects_bad_input():
    service = PlayService()
    bad = service.validate_play(units=0, legs=0, odds=0)
    assert bad is not None
    assert "units" in bad["message"].lower()


def test_validate_play_accepts_valid_input():
    service = PlayService()
    ok = service.validate_play(units=2.5, legs=2, odds=164)
    assert ok is None


def test_combine_american_odds_for_multiple_legs():
    service = PlayService()
    assert service.combine_american_odds([-110, -110]) == 264
