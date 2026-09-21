import pytest

from src.services.image_play_service import ImagePlayService


def test_image_play_validation_accepts_structured_legs():
    ImagePlayService._validate({
        "units": 2,
        "team_name": "Colts",
        "legs": [{"selection": "Moneyline", "odds": -200}],
    })


def test_image_play_validation_rejects_missing_odds():
    with pytest.raises(ValueError):
        ImagePlayService._validate({
            "units": 2,
            "legs": [{"selection": "Moneyline", "odds": 0}],
        })


def test_image_play_validation_normalizes_string_numbers():
    data = {"units": "2", "legs": [{"selection": "Moneyline", "odds": "-110"}]}
    ImagePlayService._validate(data)
    assert data["units"] == 2.0
    assert data["legs"][0]["odds"] == -110


def test_extract_units_from_message_text():
    assert ImagePlayService.extract_units_from_text("2U") == 2.0
    assert ImagePlayService.extract_units_from_text("Units: 2.5") == 2.5
    assert ImagePlayService.extract_units_from_text("$20 stake") is None