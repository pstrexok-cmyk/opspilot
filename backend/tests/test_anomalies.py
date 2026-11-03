from dataclasses import dataclass
from datetime import date, timedelta

from app.services.anomalies import detect_intake_spikes
from app.generate_sample import generate_rows


@dataclass
class MetricRow:
    date: date
    queue: str
    cases_received: int


def test_spike_requires_fourteen_prior_days_and_exceeds_one_point_five_median() -> None:
    start = date(2026, 1, 1)
    rows = [MetricRow(start + timedelta(days=day), "kyc_review", 20) for day in range(14)]
    rows.extend([
        MetricRow(start + timedelta(days=14), "kyc_review", 30),
        MetricRow(start + timedelta(days=15), "kyc_review", 31),
    ])

    alerts = detect_intake_spikes(rows)

    assert [alert["date"] for alert in alerts] == [start + timedelta(days=15)]
    assert alerts[0]["baseline_median"] == 20
    assert alerts[0]["threshold_value"] == 30
    assert alerts[0]["actual_value"] == 31
    assert "не устанавливает его причину" in alerts[0]["explanation"]


def test_synthetic_dispute_surge_is_detected_with_the_agreed_rule() -> None:
    rows = [
        MetricRow(date.fromisoformat(str(row["date"])), str(row["queue"]), int(row["cases_received"]))
        for row in generate_rows()
        if row["queue"] == "card_disputes"
    ]

    alerts = detect_intake_spikes(rows)

    assert [alert["date"] for alert in alerts] == [
        date(2026, 8, 25), date(2026, 8, 26), date(2026, 8, 27), date(2026, 8, 28)
    ]
