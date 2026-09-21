from __future__ import annotations


class TeamManagementService:
    @staticmethod
    def normalize_team_name(name: str) -> str:
        return " ".join((name or "").strip().split())

    @staticmethod
    def team_label(name: str | None, short_name: str | None) -> str:
        candidate = (name or short_name or "Unknown Team").strip()
        return candidate or "Unknown Team"

    @staticmethod
    def format_ranking_line(position: int, team_id: int, net_units: float, wins: int, losses: int, voids: int, partials: int) -> str:
        return f"{position}. Team {team_id} — {net_units:+.2f}u | W{wins} L{losses} V{voids} P{partials}"
