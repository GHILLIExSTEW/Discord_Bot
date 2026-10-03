import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.membership_access import MembershipRoleSync, WhopMembershipSync
from src.services.membership_service import MembershipService
from src.services.whop_service import WhopService, discord_identity, paid_payment
from src.member_bet_vault import ConfirmTicketModal

NOW = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)


def membership():
    return {
        "id": "mem_test", "user_id": "user_test", "account": {"id": "biz_test"},
        "plan_id": "plan_paid", "status": "active", "cancel_at_period_end": False,
        "current_period_start": "2026-10-01T12:00:00Z",
        "current_period_end": "2026-11-01T12:00:00Z", "updated_at": "2026-10-01T12:00:00Z",
    }


def user():
    return {"id": "user_test", "social_accounts": [
        {"platform": "discord", "external_id": "123", "verified": True},
    ]}


def payment():
    return {
        "id": "pay_test", "membership_id": "mem_test", "account_id": "biz_test",
        "plan_id": "plan_paid", "status": "paid", "total": {"amount": "19.99"},
        "created_at": "2026-10-01T12:00:00Z", "paid_at": "2026-10-01T12:01:00Z",
        "refunded_at": None, "refunded_amount": None, "auto_refunded": False,
        "dispute_alerted_at": None,
    }


def service(**kwargs):
    return WhopService(
        database=Mock(), api_key="test", account_id="biz_test", plan_ids={"plan_paid"},
        clock=lambda: NOW, **kwargs,
    )


def test_paid_snapshot_requires_payment_and_verified_discord_identity():
    snapshot = service().snapshot(membership(), user(), [payment()])
    assert snapshot["paid"] is True
    assert snapshot["discord_user_id"] == "123"
    assert snapshot["payment_id"] == "pay_test"


@pytest.mark.parametrize("status", ["trialing", "past_due", "canceled", "expired", "completed", "unknown"])
def test_nonactive_states_do_not_qualify_for_paid_vault(status):
    member = membership()
    member["status"] = status
    assert service().snapshot(member, user(), [payment()])["paid"] is False


def test_cancel_at_period_end_preserves_paid_access():
    member = membership()
    member["cancel_at_period_end"] = True
    assert service().snapshot(member, user(), [payment()])["paid"] is True


@pytest.mark.parametrize("days", [30, 90, 180, 365])
def test_completed_prepaid_purchase_requires_verified_expiring_plan(days):
    member = membership()
    member["status"] = "completed"
    plan = {"id": "plan_paid", "account": {"id": "biz_test"}, "plan_type": "one_time", "expiration_days": days}
    assert service().snapshot(member, user(), [payment()], plan)["paid"] is True
    assert not service().snapshot(member, user(), [], plan)["paid"]
    assert not service().snapshot(member, user(), [payment()], {**plan, "expiration_days": None})["paid"]
    assert not service().snapshot(member, user(), [payment()], {**plan, "plan_type": "renewal"})["paid"]
    assert not service().snapshot(member, user(), [payment()], {**plan, "id": "plan_other"})["paid"]
    member["current_period_end"] = NOW.isoformat()
    assert not service().snapshot(member, user(), [payment()], plan)["paid"]


@pytest.mark.parametrize("field,value", [
    ("status", "open"), ("total", {"amount": "0.00"}), ("refunded_at", "2026-10-03T10:00:00Z"),
    ("refunded_amount", {"amount": "1.00"}), ("auto_refunded", True),
    ("dispute_alerted_at", "2026-10-03T10:00:00Z"), ("account_id", "biz_other"),
    ("membership_id", "mem_other"), ("plan_id", "plan_other"),
    ("paid_at", None), ("created_at", "2026-09-01T12:00:00Z"),
])
def test_payment_failures_refunds_old_cycles_and_other_sellers_do_not_grant_access(field, value):
    pay = payment()
    pay[field] = value
    assert service().snapshot(membership(), user(), [pay])["paid"] is False


def test_missing_free_or_unclaimed_membership_denied():
    assert not service().snapshot(membership(), user(), [])["paid"]
    assert not service().snapshot(membership(), None, [payment()])["paid"]
    member = membership()
    member["current_period_end"] = None
    assert not service().snapshot(member, user(), [payment()])["paid"]


def test_expiry_boundary():
    member = membership()
    member["current_period_end"] = NOW.isoformat()
    assert not service().snapshot(member, user(), [payment()])["paid"]


def test_wrong_seller_plan_or_buyer_rejected():
    member = membership()
    member["account"]["id"] = "biz_other"
    with pytest.raises(ValueError, match="different seller"):
        service().snapshot(member, user(), [])
    member = membership()
    member["plan_id"] = "plan_free"
    with pytest.raises(ValueError, match="not approved"):
        service().snapshot(member, user(), [])
    wrong_user = user()
    wrong_user["id"] = "user_other"
    with pytest.raises(ValueError, match="buyer"):
        service().snapshot(membership(), wrong_user, [])


def test_unverified_ambiguous_or_missing_discord_identity_denied():
    account = user()
    account["social_accounts"][0]["verified"] = False
    assert discord_identity(account) is None
    account = user()
    account["social_accounts"].append({"platform": "discord", "external_id": "456", "verified": True})
    assert discord_identity(account) is None
    with pytest.raises(ValueError):
        discord_identity({"id": "user_test"})


def test_pagination_reads_all_pages_and_pins_api_version():
    response = Mock()
    response.json.side_effect = [
        {"data": [{"id": "one"}], "page_info": {"has_next_page": True, "end_cursor": "cursor"}},
        {"data": [{"id": "two"}], "page_info": {"has_next_page": False}},
    ]
    get = Mock(return_value=response)
    assert [row["id"] for row in service(get=get).pages("memberships", {"account_id": "biz_test"})] == ["one", "two"]
    assert get.call_args.kwargs["params"]["after"] == "cursor"
    assert get.call_args.kwargs["headers"]["Api-Version-Date"] == "2026-09-29"


def test_repeated_cursor_is_error_not_silent_partial_sync():
    whop = service()
    whop.request = Mock(return_value={"data": [], "page_info": {"has_next_page": True, "end_cursor": "same"}})
    with pytest.raises(RuntimeError, match="pagination cursor"):
        list(whop.pages("memberships", {}))


def test_sync_filters_plans_and_checks_current_payment():
    whop = service()
    whop.ready = Mock()
    free = {**membership(), "plan_id": "plan_free"}
    whop.pages = Mock(side_effect=[[free, membership()], [payment()]])
    whop.request = Mock(return_value=user())
    whop.save = Mock()
    assert whop.sync() == 1
    assert whop.save.call_args.args[0]["paid"] is True
    whop.request.assert_called_once_with("users/user_test")


def test_membership_rpc_requires_boolean_and_never_falls_back_to_roles():
    db = Mock()
    result = db._ensure_client.return_value.rpc.return_value.execute.return_value
    result.data = True
    access = MembershipService(db)
    assert access.has_paid_access(123)
    result.data = "true"
    with pytest.raises(RuntimeError, match="invalid access"):
        access.has_paid_access(123)


def test_failed_whop_sync_does_not_remove_discord_roles(caplog):
    async def run():
        whop = Mock()
        whop.sync.side_effect = RuntimeError("API unavailable")
        roles = SimpleNamespace(sync=AsyncMock())
        sync = WhopMembershipSync(Mock(), roles, whop)
        await sync.reconcile()
        roles.sync.assert_not_awaited()
    asyncio.run(run())
    assert "whop_membership_reconciliation_failed" in caplog.text


def test_paid_confirmation_is_rechecked_and_expired_draft_not_confirmed():
    async def run():
        vault = SimpleNamespace(
            lock=asyncio.Lock(), membership=Mock(), service=Mock(), publish=AsyncMock(),
        )
        vault.membership.has_paid_access.return_value = False
        modal = ConfirmTicketModal(vault, {
            "id": 1, "units": 1, "odds": -110, "details": {"game": "Home vs Away"},
        })
        modal.units._value = "1"
        modal.odds._value = "-110"
        interaction = SimpleNamespace(
            user=SimpleNamespace(id=123), response=SimpleNamespace(defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )
        await modal.on_submit(interaction)
        vault.service.confirm.assert_not_called()
        assert "current paid membership" in interaction.followup.send.call_args.args[0]
    asyncio.run(run())


def test_roles_add_paid_and_remove_nonpaying_without_affecting_other_roles():
    class Role:
        id = 77
        managed = False
        permissions = SimpleNamespace(administrator=False, manage_guild=False, manage_roles=False)

        def is_default(self):
            return False

        def __ge__(self, other):
            return False

    async def run():
        role = Role()
        paid = SimpleNamespace(id=123, bot=False, roles=[], add_roles=AsyncMock(), remove_roles=AsyncMock())
        expired = SimpleNamespace(id=456, bot=False, roles=[role], add_roles=AsyncMock(), remove_roles=AsyncMock())

        async def fetch_members(limit):
            yield paid
            yield expired

        guild = SimpleNamespace(
            id=1, me=SimpleNamespace(guild_permissions=SimpleNamespace(manage_roles=True), top_role=object()),
            get_role=lambda role_id: role, fetch_members=fetch_members,
        )
        access = Mock()
        access.paid_discord_ids.return_value = {123}
        sync = MembershipRoleSync(SimpleNamespace(get_guild=lambda guild_id: guild), 1, 77, access)
        await sync.sync()
        paid.add_roles.assert_awaited_once()
        expired.remove_roles.assert_awaited_once()
        paid.remove_roles.assert_not_awaited()
    asyncio.run(run())
