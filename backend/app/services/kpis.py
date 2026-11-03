from decimal import Decimal
from typing import Any, Iterable


def _number(value: Any) -> float:
    return float(value) if isinstance(value, Decimal) else float(value or 0)


def calculate_kpis(rows: Iterable[Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Summarize filtered daily queue rows and retain the daily series for charts."""
    ordered_rows = sorted(rows, key=lambda row: (row.date, row.queue))
    received = sum(row.cases_received for row in ordered_rows)
    resolved = sum(row.cases_resolved for row in ordered_rows)
    breaches = sum(row.sla_breaches for row in ordered_rows)
    reopened = sum(row.reopened_cases for row in ordered_rows)

    weighted_resolution_total = sum(
        _number(row.avg_resolution_hours) * row.cases_resolved for row in ordered_rows
    )
    weighted_resolution = weighted_resolution_total / resolved if resolved else None

    # Only the last backlog observation in the selected period counts for each queue.
    latest_by_queue: dict[str, Any] = {}
    for row in ordered_rows:
        latest_by_queue[row.queue] = row
    latest_backlog = sum(row.backlog_end for row in latest_by_queue.values())

    daily_csat = [_number(row.csat_avg) for row in ordered_rows if row.csat_avg is not None]
    summary = {
        "cases_received": received,
        "cases_resolved": resolved,
        "backlog_end": latest_backlog,
        "sla_breaches": breaches,
        "sla_breach_rate_pct": round(100 * breaches / resolved, 2) if resolved else None,
        "throughput_to_intake_pct": round(100 * resolved / received, 2) if received else None,
        "weighted_avg_resolution_hours": round(weighted_resolution, 2) if weighted_resolution is not None else None,
        "reopened_cases": reopened,
        # The source is a daily average with no response count, so this is unweighted.
        "average_daily_csat": round(sum(daily_csat) / len(daily_csat), 2) if daily_csat else None,
    }

    series = []
    for row in ordered_rows:
        series.append({
            "date": row.date,
            "queue": row.queue,
            "cases_received": row.cases_received,
            "cases_resolved": row.cases_resolved,
            "backlog_end": row.backlog_end,
            "avg_resolution_hours": _number(row.avg_resolution_hours),
            "sla_breaches": row.sla_breaches,
            "sla_breach_rate_pct": round(100 * row.sla_breaches / row.cases_resolved, 2)
            if row.cases_resolved else None,
            "reopened_cases": row.reopened_cases,
            "csat_avg": _number(row.csat_avg) if row.csat_avg is not None else None,
        })
    return summary, series

