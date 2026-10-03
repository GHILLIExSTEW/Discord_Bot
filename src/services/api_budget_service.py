from contextvars import ContextVar
from contextlib import contextmanager
from urllib.parse import urlparse

from src.config import API_SPORTS_BUDGET_ENABLED
from src.services.supabase_service import supabase_service

member_request_user = ContextVar("member_request_user", default=None)
reserved_batch = ContextVar("reserved_batch", default=None)


class ApiBudgetDenied(RuntimeError):
    pass


def api_product(base_url: str) -> str:
    hostname = urlparse(base_url).hostname or ""
    parts = hostname.split(".")
    if len(parts) != 4 or parts[-2:] != ["api-sports", "io"]:
        raise RuntimeError("Cannot budget an unknown API-Sports host.")
    return parts[1]


@contextmanager
def member_request_batch(base_url: str, user_id: int, count: int):
    if not API_SPORTS_BUDGET_ENABLED:
        raise ApiBudgetDenied("Live refresh is disabled until the shared budget is activated.")
    if type(count) is not int or not 1 <= count <= 5:
        raise ValueError("A player lookup must reserve between one and five requests.")
    if reserved_batch.get() is not None:
        raise RuntimeError("Nested API request batches are not supported.")
    product = api_product(base_url)
    result = supabase_service._ensure_client().rpc("reserve_api_requests", {
        "p_product": product, "p_discord_user_id": str(user_id), "p_requests": count,
    }).execute().data
    if not isinstance(result, str):
        raise RuntimeError("API budget returned an invalid response.")
    if result != "reserved":
        raise ApiBudgetDenied(result)
    user_token = member_request_user.set(str(user_id))
    batch_token = reserved_batch.set({"product": product, "remaining": count})
    try:
        yield
    finally:
        reserved_batch.reset(batch_token)
        member_request_user.reset(user_token)


def reserve_request(base_url: str) -> None:
    batch = reserved_batch.get()
    if batch is not None:
        if api_product(base_url) != batch["product"] or batch["remaining"] <= 0:
            raise ApiBudgetDenied("Player lookup exceeded its reserved API requests.")
        batch["remaining"] -= 1
        return
    if not API_SPORTS_BUDGET_ENABLED:
        if member_request_user.get() is not None:
            raise ApiBudgetDenied("Live refresh is disabled until the shared budget is activated.")
        return
    product = api_product(base_url)
    result = supabase_service._ensure_client().rpc(
        "reserve_api_request", {
            "p_product": product, "p_discord_user_id": member_request_user.get(),
        },
    ).execute().data
    if not isinstance(result, str):
        raise RuntimeError("API budget returned an invalid response.")
    if result != "reserved":
        raise ApiBudgetDenied(result)
