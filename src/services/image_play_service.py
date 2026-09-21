from __future__ import annotations

import json
from typing import Any

import requests

from src.config import OPENAI_API_KEY, OPENAI_VISION_MODEL


class ImagePlayService:
    def extract_play(self, image_url: str) -> dict[str, Any]:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": OPENAI_VISION_MODEL,
                "response_format": {"type": "json_object"},
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Read this betting slip. Return JSON only with keys: "
                                "units (number), team_name (string or null), and legs (array). "
                                "Each legs item must have selection (string) and odds (integer). "
                                "Do not guess unreadable text; use an empty string and explain uncertainty "
                                "in the selection."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }],
            },
            timeout=60,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
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