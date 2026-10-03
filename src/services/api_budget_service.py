from contextvars import ContextVar
from urllib.parse import urlparse

from src.config import API_SPORTS_BUDGET_ENABLED
from src.services.supabase_service import supabase_service

member_request_user = ContextVar("member_request_user", default=None)


class ApiBudgetDenied(RuntimeError):
    pass


def reserve_request(base_url: str) -> None:
    if not API_SPORTS_BUDGET_ENABLED:
        if member_request_user.get() is not None:
            raise ApiBudgetDenied("Live refresh is disabled until the shared budget is activated.")
        return
    hostname = urlparse(base_url).hostname or ""
    parts = hostname.split(".")
    if len(parts) != 4 or parts[-2:] != ["api-sports", "io"]:
        raise RuntimeError("Cannot budget an unknown API-Sports host.")
    product = parts[1]
    result = supabase_service._ensure_client().rpc(
        "reserve_api_request", {
            "p_product": product, "p_discord_user_id": member_request_user.get(),
        },
    ).execute().data
    if not isinstance(result, str):
        raise RuntimeError("API budget returned an invalid response.")
    if result != "reserved":
        raise ApiBudgetDenied(result)
