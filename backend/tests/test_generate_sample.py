from statistics import median

from app.generate_sample import DAYS, QUEUES, generate_rows


def test_sample_history_is_repeatable_and_has_one_row_per_day_and_queue() -> None:
    first = generate_rows()
    second = generate_rows()

    assert first == second
    assert len(first) == DAYS * len(QUEUES) == 270


def test_card_disputes_surge_is_visible_in_generated_data() -> None:
    rows = [row for row in generate_rows() if row["queue"] == "card_disputes"]
    baseline = [row["cases_received"] for row in rows[:55]]
    surge = [row["cases_received"] for row in rows[55:59]]

    assert min(surge) > median(baseline) * 2

