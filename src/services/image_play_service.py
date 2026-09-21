from __future__ import annotations

import json
from typing import Any

import requests

from src.config import (
    OPENAI_API_KEY,
    OPENAI_VISION_MODEL,
    VISION_FALLBACK_API_KEY,
    VISION_FALLBACK_MODEL,
    VISION_FALLBACK_URL,
)


class ImagePlayService:
    PROMPT = (
        "Read this betting slip. Return JSON only with keys: units (number), "
        "team_name (string or null), and legs (array). Each legs item must have "
        "selection (string) and odds (integer). Do not guess unreadable text; "
        "explain uncertainty in the selection."
    )

    def extract_play(self, image_url: str) -> dict[str, Any]:
        errors = []
        providers = []
        if OPENAI_API_KEY:
            providers.append(("openai", "https://api.openai.com/v1/chat/completions", OPENAI_API_KEY, OPENAI_VISION_MODEL))
        if VISION_FALLBACK_URL and VISION_FALLBACK_API_KEY and VISION_FALLBACK_MODEL:
            providers.append(("fallback", VISION_FALLBACK_URL, VISION_FALLBACK_API_KEY, VISION_FALLBACK_MODEL))
        if not providers:
            raise RuntimeError("No vision provider is configured.")

        for name, url, api_key, model in providers:
            try:
                return self._extract_with_provider(image_url, name, url, api_key, model)
            except Exception as exc:
                errors.append(f"{name}: {exc}")

        raise RuntimeError("All vision providers failed or blocked the image. " + " | ".join(errors))

    def _extract_with_provider(self, image_url: str, name: str, url: str, api_key: str, model: str) -> dict[str, Any]:
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": self.PROMPT},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ]}],
            },
            timeout=60,
        )
        if response.status_code in {400, 403, 408, 429} or response.status_code >= 500:
            raise RuntimeError(f"provider response {response.status_code}")
        response.raise_for_status()
        body = response.json()
        choice = (body.get("choices") or [{}])[0]
        finish_reason = choice.get("finish_reason")
        if finish_reason in {"blocked", "content_filter", "safety"}:
            raise RuntimeError(f"provider blocked image ({finish_reason})")
        content = (choice.get("message") or {}).get("content")
        if not content:
            raise RuntimeError("provider returned no content")
        parsed = json.loads(content)
        self._validate(parsed)
        return parsed

    @staticmethod
    def _validate(data: dict[str, Any]) -> None:
        if not isinstance(data.get("units"), (int, float)) or data["units"] <= 0:
            raise ValueError("The image reader could not find valid units.")
        legs = data.get("legs")
        if not isinstance(legs, list) or not 1 <= len(legs) <= 10:
            raise ValueError("The image reader could not find 1-10 legs.")
        for leg in legs:
            if not isinstance(leg.get("selection"), str) or not leg["selection"].strip():
                raise ValueError("At least one leg selection could not be read.")
            if not isinstance(leg.get("odds"), int) or leg["odds"] == 0:
                raise ValueError("At least one leg's odds could not be read.")


image_play_service = ImagePlayService()