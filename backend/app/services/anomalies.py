from datetime import date, timedelta
from statistics import median
from typing import Any, Iterable


WINDOW_DAYS = 28
MIN_BASELINE_DAYS = 14
MULTIPLIER = 1.5


def _ru_number(value: float) -> str:
    return f"{value:g}".replace(".", ",")


def detect_intake_spikes(rows: Iterable[Any]) -> list[dict[str, Any]]:
    """Flag unusually high daily intake against the preceding 28 calendar days."""
    ordered = sorted(rows, key=lambda row: (row.queue, row.date))
    by_queue: dict[str, list[Any]] = {}
    for row in ordered:
        by_queue.setdefault(row.queue, []).append(row)

    alerts: list[dict[str, Any]] = []
    for queue, queue_rows in by_queue.items():
        left = 0
        for index, row in enumerate(queue_rows):
            first_day = row.date - timedelta(days=WINDOW_DAYS)
            while left < index and queue_rows[left].date < first_day:
                left += 1
            prior = [
                previous.cases_received for previous in queue_rows[left:index]
            ]
            if len(prior) < MIN_BASELINE_DAYS:
                continue

            baseline = float(median(prior))
            threshold = baseline * MULTIPLIER
            actual = float(row.cases_received)
            if actual <= threshold:
                continue

            ratio = actual / baseline if baseline else float("inf")
            alerts.append({
                "date": row.date,
                "queue": queue,
                "metric_name": "cases_received",
                "actual_value": actual,
                "baseline_median": baseline,
                "threshold_value": threshold,
                "baseline_days": len(prior),
                "method": "median_previous_28_calendar_days",
                "severity": "high" if ratio >= 2 else "attention",
                "explanation": (
                    f"Поступило {int(actual)} кейсов — больше порога {_ru_number(threshold)} "
                    f"(1,5 × медиана {_ru_number(baseline)} за {len(prior)} наблюдений "
                    "в предыдущие 28 календарных дней). Сигнал показывает необычный объём, "
                    "но не устанавливает его причину."
                ),
            })

    return sorted(alerts, key=lambda alert: (alert["date"], alert["queue"]))
