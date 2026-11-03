from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.services.kpis import calculate_kpis


@dataclass
class MetricRow:
    date: date
    queue: str
    cases_received: int
    cases_resolved: int
    backlog_end: int
    avg_resolution_hours: Decimal
    sla_breaches: int
    reopened_cases: int
    csat_avg: Decimal | None


def test_kpis_use_latest_backlog_and_weighted_resolution_time() -> None:
    rows = [
        MetricRow(date(2026, 7, 1), "kyc_review", 20, 10, 30, Decimal("10"), 1, 1, Decimal("4.0")),
        MetricRow(date(2026, 7, 2), "kyc_review", 40, 30, 25, Decimal("20"), 3, 0, Decimal("4.5")),
        MetricRow(date(2026, 7, 2), "card_disputes", 100, 50, 50, Decimal("30"), 10, 2, None),
    ]

    summary, series = calculate_kpis(rows)

    assert summary["cases_received"] == 160
    assert summary["cases_resolved"] == 90
    assert summary["backlog_end"] == 75  # Last KYC backlog (25) + last disputes backlog (50).
    assert summary["sla_breach_rate_pct"] == 15.56
    assert summary["throughput_to_intake_pct"] == 56.25
    assert summary["weighted_avg_resolution_hours"] == 24.44
    assert summary["average_daily_csat"] == 4.25
    assert [point["queue"] for point in series] == ["kyc_review", "card_disputes", "kyc_review"]


def test_zero_denominators_return_no_data() -> None:
    rows = [
        MetricRow(date(2026, 7, 1), "kyc_review", 0, 0, 0, Decimal("0"), 0, 0, None),
    ]

    summary, series = calculate_kpis(rows)

    assert summary["sla_breach_rate_pct"] is None
    assert summary["throughput_to_intake_pct"] is None
    assert summary["weighted_avg_resolution_hours"] is None
    assert summary["average_daily_csat"] is None
    assert series[0]["sla_breach_rate_pct"] is None
