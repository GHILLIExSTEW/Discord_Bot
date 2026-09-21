from unittest.mock import Mock, patch

from src.services.image_play_service import ImagePlayService


def test_image_parser_uses_fallback_after_primary_block():
    service = ImagePlayService()
    blocked = Mock(status_code=400)
    fallback = Mock(status_code=200)
    fallback.json.return_value = {
        "choices": [{"finish_reason": "stop", "message": {"content": '{"units": 2, "legs": [{"selection": "Moneyline", "odds": -110}]}'}}]
    }
    with patch("src.services.image_play_service.OPENAI_API_KEY", "primary"), patch(
        "src.services.image_play_service.OPENAI_VISION_MODELS", ["primary-model", "fallback-model"]
    ), patch(
        "src.services.image_play_service.requests.post", side_effect=[blocked, fallback]
    ):
        result = service.extract_play("https://example.test/slip.png")

    assert result["units"] == 2
    assert fallback.status_code == 200


def test_image_parser_accepts_fenced_json():
    service = ImagePlayService()
    response = Mock(status_code=200)
    response.json.return_value = {
        "choices": [{"finish_reason": "stop", "message": {"content": "```json\n{\"units\": \"2\", \"legs\": [{\"selection\": \"Moneyline\", \"odds\": \"-110\"}]}\n```"}}]
    }
    with patch("src.services.image_play_service.OPENAI_API_KEY", "primary"), patch(
        "src.services.image_play_service.OPENAI_VISION_MODELS", ["gpt-5.4-mini"]
    ), patch("src.services.image_play_service.requests.post", return_value=response):
        result = service.extract_play("https://example.test/slip.png")

    assert result["units"] == 2
    assert result["legs"][0]["odds"] == -110