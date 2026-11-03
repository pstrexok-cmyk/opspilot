from datetime import date

from app.services.reports import build_management_report


def test_template_report_repeats_calculated_facts_and_discloses_method() -> None:
    facts, narrative = build_management_report(
        period_from=date(2026, 8, 1),
        period_to=date(2026, 8, 31),
        queue="card_disputes",
        summary={
            "cases_received": 100,
            "cases_resolved": 95,
            "backlog_end": 50,
            "sla_breaches": 5,
            "sla_breach_rate_pct": 5.26,
            "throughput_to_intake_pct": 95.0,
            "weighted_avg_resolution_hours": 24.5,
            "average_daily_csat": 4.2,
        },
        anomaly_count=2,
        language="ru",
    )

    assert facts["cases_received"] == 100
    assert facts["anomaly_count"] == 2
    assert "Поступило на 5 кейсов больше" in narrative
    assert "5,26%" in narrative
    assert "2 сигнала необычного объёма" in narrative
    assert "AI не использовался" in narrative


def test_report_supports_english_and_preserves_the_same_facts() -> None:
    summary = {
        "cases_received": 100,
        "cases_resolved": 95,
        "backlog_end": 50,
        "sla_breaches": 5,
        "sla_breach_rate_pct": 5.26,
        "throughput_to_intake_pct": 95.0,
        "weighted_avg_resolution_hours": 24.5,
        "average_daily_csat": 4.2,
    }
    facts, narrative = build_management_report(
        period_from=date(2026, 8, 1),
        period_to=date(2026, 8, 31),
        queue="card_disputes",
        summary=summary,
        anomaly_count=2,
        language="en",
    )

    assert facts["cases_received"] == 100
    assert facts["language"] == "en"
    assert "100 cases received and 95 cases resolved" in narrative
    assert "5.26%" in narrative
    assert "2 unusual intake signals" in narrative
    assert "no AI was used" in narrative
