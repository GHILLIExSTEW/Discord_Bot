from src.services.team_management_service import TeamManagementService


def test_format_ranking_line_uses_signed_units():
    line = TeamManagementService.format_ranking_line(
        position=1,
        team_id=42,
        net_units=12.5,
        wins=7,
        losses=2,
        voids=1,
        partials=3,
    )
    assert line == "1. Team 42 — +12.50u | W7 L2 V1 P3"


def test_normalize_team_name_removes_extra_spaces():
    assert TeamManagementService.normalize_team_name("  Team    Alpha  ") == "Team Alpha"


def test_team_label_builds_from_short_name_or_name():
    assert TeamManagementService.team_label("Alpha", "A") == "Alpha"
    assert TeamManagementService.team_label("Beta", None) == "Beta"
