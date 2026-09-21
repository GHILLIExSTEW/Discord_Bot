from typing import Any

import requests

from src.config import API_SPORTS_KEY

BASE_URLS = {
    "volleyball": "https://v1.volleyball.api-sports.io",
    "american-football": "https://v1.american-football.api-sports.io",
    "basketball": "https://v1.basketball.api-sports.io",
}


class ApiSportsService:
    def __init__(self) -> None:
        self.api_key = API_SPORTS_KEY

    def get_for_sport(
        self,
        sport_slug: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("API_SPORTS_KEY is not configured.")
        try:
            base_url = BASE_URLS[sport_slug]
        except KeyError as exc:
            raise ValueError(f"Unsupported API-Sports slug: {sport_slug}") from exc

        url = f"{base_url}/{endpoint.strip('/')}"
        response = requests.get(
            url,
            headers={"x-apisports-key": self.api_key},
            params=params or {},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.get_for_sport("volleyball", endpoint, params)


api_sports_service = ApiSportsService()
