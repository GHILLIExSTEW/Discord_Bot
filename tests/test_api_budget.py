from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from src.services.api_budget_service import ApiBudgetDenied, member_request_user, reserve_request


@pytest.mark.parametrize("host", ["v1.american-football.api-sports.io", "v1.basketball.api-sports.io"])
def test_reservation_before_provider_request(host):
    client = Mock()
    client.rpc.return_value.execute.return_value.data = "reserved"
    token = member_request_user.set("123")
    try:
        with patch("src.services.api_budget_service.API_SPORTS_BUDGET_ENABLED", True), patch(
            "src.services.api_budget_service.supabase_service._ensure_client", return_value=client,
        ):
            reserve_request("https://" + host)
        client.rpc.assert_called_once_with("reserve_api_request", {
            "p_product": host.split(".")[1], "p_discord_user_id": "123",
        })
    finally:
        member_request_user.reset(token)


def test_member_calls_fail_closed_without_budget():
    token = member_request_user.set("123")
    try:
        with patch("src.services.api_budget_service.API_SPORTS_BUDGET_ENABLED", False), pytest.raises(ApiBudgetDenied):
            reserve_request("https://v1.basketball.api-sports.io")
    finally:
        member_request_user.reset(token)


@pytest.mark.parametrize("response", ["Shared member daily allowance exhausted", "Your five-refresh daily allowance is exhausted"])
def test_budget_denial_is_explicit(response):
    client = Mock()
    client.rpc.return_value.execute.return_value.data = response
    with patch("src.services.api_budget_service.API_SPORTS_BUDGET_ENABLED", True), patch(
        "src.services.api_budget_service.supabase_service._ensure_client", return_value=client,
    ), pytest.raises(ApiBudgetDenied, match=response):
        reserve_request("https://v1.basketball.api-sports.io")


def test_all_provider_callers_consult_shared_budget():
    from src.services.api_sports_service import ApiSportsService
    from src.services.api_sports_multi_service import ApiSportsMultiService
    get = Mock()
    for module, call in [
        ("src.services.api_sports_service", lambda: ApiSportsService(api_key="test", get=get)._request("games")),
        ("src.services.api_sports_multi_service", lambda: ApiSportsMultiService(api_key="test", get=get)._request("https://v1.basketball.api-sports.io", "games", {})),
    ]:
        with patch(module + ".reserve_request", side_effect=ApiBudgetDenied("exhausted")), pytest.raises(ApiBudgetDenied):
            call()
    get.assert_not_called()


def test_season_transport_rejects_paginated_response_instead_of_silent_partial_data():
    from src.services.api_sports_multi_service import ApiSportsMultiService
    get = Mock()
    get.return_value.json.return_value = {
        "errors": [], "paging": {"current": 1, "total": 2}, "response": [],
    }
    with patch("src.services.api_sports_multi_service.reserve_request"), pytest.raises(ValueError, match="additional provider pages"):
        ApiSportsMultiService(api_key="test", get=get)._request(
            "https://v3.football.api-sports.io", "players", {}, require_complete=True,
        )
