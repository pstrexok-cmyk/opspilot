from app.services.csv_import import validate_csv


HEADER = (
    "date,queue,cases_received,cases_resolved,backlog_end,avg_resolution_hours,"
    "sla_breaches,reopened_cases,csat_avg\n"
)


def test_valid_csv_allows_blank_csat() -> None:
    content = (HEADER + "2026-07-01,kyc_review,12,10,5,4.25,1,0,\n").encode()

    result = validate_csv(content, "daily.csv")

    assert result.success is True
    assert result.records[0]["csat_avg"] is None
    assert result.records[0]["cases_received"] == 12


def test_invalid_date_and_negative_count_are_reported() -> None:
    content = (HEADER + "not-a-date,card_disputes,-3,4,2,5,1,0,4.2\n").encode()

    result = validate_csv(content, "daily.csv")

    assert result.success is False
    assert {issue["code"] for issue in result.errors} == {"invalid_date", "negative_value"}
    assert result.records == []


def test_duplicate_date_and_queue_are_rejected() -> None:
    row = "2026-07-01,payments_support,12,10,5,4.25,1,0,4.2\n"
    result = validate_csv((HEADER + row + row).encode(), "daily.csv")

    assert result.success is False
    assert any(issue["code"] == "duplicate_date_queue" and issue["row"] == 3 for issue in result.errors)


def test_only_the_three_northstar_queues_are_accepted() -> None:
    content = (HEADER + "2026-07-01,loans,12,10,5,4.25,1,0,4.2\n").encode()
    result = validate_csv(content, "daily.csv")

    assert result.success is False
    assert result.errors[0]["code"] == "invalid_queue"

