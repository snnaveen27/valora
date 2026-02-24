import pytest

from core.sqlite_pool import close_all_pools
from services.digital_employee_service import DigitalEmployeeService


class FakeQueryService:
    def __init__(self, results=None):
        self.results = results or []

    def search_properties(self, **kwargs):
        return list(self.results)


def test_free_tier_alert_limit(tmp_path):
    service = DigitalEmployeeService(db_path=tmp_path / "digital_employee_test.db")
    service._query_service = FakeQueryService([])

    payload = {
        "name": "Test Alert",
        "criteria": {"locality": "Andheri"},
        "frequency": "instant",
        "channels": ["in_app"],
    }

    service.create_alert("user@example.com", "free", payload)
    service.create_alert("user@example.com", "free", payload)
    service.create_alert("user@example.com", "free", payload)

    with pytest.raises(PermissionError):
        service.create_alert("user@example.com", "free", payload)


def test_parse_alert_command():
    service = DigitalEmployeeService(db_path=":memory:")
    parsed = service.parse_command("Alert me when 2BHK in Andheri under 70L is listed")
    assert parsed["handled"] is True
    assert parsed["intent"] == "create_alert"
    assert parsed["payload"]["criteria"]["locality"] == "Andheri"
    assert parsed["payload"]["criteria"]["bhk"] == 2


def test_alert_scan_triggers_once_for_same_fingerprint(tmp_path):
    service = DigitalEmployeeService(db_path=tmp_path / "digital_employee_scan.db")
    service._query_service = FakeQueryService(
        [{"id": 101, "title": "Listing A", "price": 6_500_000, "locality": "Andheri"}]
    )

    service.create_alert(
        "pro@example.com",
        "pro",
        {
            "criteria": {"locality": "Andheri"},
            "frequency": "instant",
            "channels": ["in_app"],
        },
    )

    first = service.run_alert_scan_cycle(now_ts=1_000)
    assert first["triggered"] == 1

    # Same fingerprint after enough interval should not trigger again.
    second = service.run_alert_scan_cycle(now_ts=5_000)
    assert second["triggered"] == 0


def test_services_with_different_db_paths_are_isolated(tmp_path):
    close_all_pools()
    db_a = tmp_path / "digital_employee_a.db"
    db_b = tmp_path / "digital_employee_b.db"

    service_a = DigitalEmployeeService(db_path=db_a)
    service_b = DigitalEmployeeService(db_path=db_b)

    payload = {
        "name": "A Alert",
        "criteria": {"locality": "Andheri"},
        "frequency": "instant",
        "channels": ["in_app"],
    }

    service_a.create_alert("iso@example.com", "free", payload)

    alerts_a = service_a.list_alerts("iso@example.com")
    alerts_b = service_b.list_alerts("iso@example.com")

    assert len(alerts_a) == 1
    assert alerts_b == []
