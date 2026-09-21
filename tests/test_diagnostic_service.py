from src.services.diagnostic_service import DiagnosticService


def test_diagnostic_service_runs_all_safe_checks():
    checks = DiagnosticService().run_checks()
    assert len(checks) == 5
    assert all(check["passed"] for check in checks)