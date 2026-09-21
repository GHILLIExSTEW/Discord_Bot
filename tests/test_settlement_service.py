from src.services.settlement_service import SettlementService


def test_tally_for_win():
    assert SettlementService.tally_for_result("win", 10) == 10.0


def test_tally_for_loss():
    assert SettlementService.tally_for_result("loss", 10) == -10.0


def test_tally_for_partial():
    assert SettlementService.tally_for_result("partial", 10) == 5.0


def test_regrade_validates_payload():
    result = SettlementService.validate_regrade(legs_left=2, odds=164)
    assert result["legs_left"] == 2
    assert result["odds"] == 164
