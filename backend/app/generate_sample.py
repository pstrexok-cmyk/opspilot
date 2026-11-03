import csv
import random
from datetime import date, timedelta
from pathlib import Path


START_DATE = date(2026, 7, 1)
DAYS = 90
OUTPUT = Path(__file__).resolve().parents[2] / "sample-data" / "northstar_daily_operations.csv"

QUEUES = {
    "kyc_review": {"incoming": 165, "capacity": 170, "resolution_hours": 18.0},
    "card_disputes": {"incoming": 42, "capacity": 48, "resolution_hours": 30.0},
    "payments_support": {"incoming": 235, "capacity": 245, "resolution_hours": 5.5},
}

FIELDS = [
    "date",
    "queue",
    "cases_received",
    "cases_resolved",
    "backlog_end",
    "avg_resolution_hours",
    "sla_breaches",
    "reopened_cases",
    "csat_avg",
]


def generate_rows() -> list[dict[str, str | int | float]]:
    """Build 90 reproducible days; days 56–59 contain a card-disputes volume surge."""
    rng = random.Random(42)
    backlog = {queue: starting for queue, starting in {
        "kyc_review": 310,
        "card_disputes": 95,
        "payments_support": 180,
    }.items()}
    rows: list[dict[str, str | int | float]] = []

    for offset in range(DAYS):
        current_date = START_DATE + timedelta(days=offset)
        for queue, profile in QUEUES.items():
            received = max(0, round(rng.gauss(profile["incoming"], profile["incoming"] * 0.08)))
            capacity = max(1, round(rng.gauss(profile["capacity"], profile["capacity"] * 0.04)))

            # A four-day dispute surge creates a clear, explainable operational event.
            if queue == "card_disputes" and 55 <= offset <= 58:
                received = round(received * 2.2)

            available_to_resolve = backlog[queue] + received
            resolved = min(available_to_resolve, capacity)
            backlog[queue] = available_to_resolve - resolved

            pressure = backlog[queue] / profile["capacity"]
            avg_resolution_hours = max(
                0.5,
                profile["resolution_hours"] * (1 + min(pressure * 0.025, 1.1)) + rng.uniform(-1.2, 1.2),
            )
            breach_rate = min(0.03 + pressure * 0.012, 0.35)
            sla_breaches = min(resolved, round(resolved * breach_rate))
            reopened_cases = min(resolved, round(resolved * rng.uniform(0.015, 0.045)))
            csat_avg = max(2.5, min(4.9, 4.7 - min(pressure * 0.035, 1.8) + rng.uniform(-0.12, 0.12)))

            rows.append({
                "date": current_date.isoformat(),
                "queue": queue,
                "cases_received": received,
                "cases_resolved": resolved,
                "backlog_end": backlog[queue],
                "avg_resolution_hours": round(avg_resolution_hours, 2),
                "sla_breaches": sla_breaches,
                "reopened_cases": reopened_cases,
                "csat_avg": round(csat_avg, 2),
            })
    return rows


def write_sample(path: Path = OUTPUT) -> int:
    rows = generate_rows()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    count = write_sample()
    print(f"Created {count} synthetic daily queue records at {OUTPUT}")

