from datetime import date
from typing import Any


def _ru_number(value: int | float, decimals: int = 0) -> str:
    return format(value, f",.{decimals}f").replace(",", " ").replace(".", ",")


def _en_number(value: int | float, decimals: int = 0) -> str:
    return format(value, f",.{decimals}f")


def _signal_word(count: int) -> str:
    remainder_100 = count % 100
    remainder_10 = count % 10
    if 11 <= remainder_100 <= 14:
        return "сигналов"
    if remainder_10 == 1:
        return "сигнал"
    if 2 <= remainder_10 <= 4:
        return "сигнала"
    return "сигналов"


def _case_phrase(count: int) -> str:
    remainder_100 = count % 100
    remainder_10 = count % 10
    if 11 <= remainder_100 <= 14 or remainder_10 == 0 or remainder_10 >= 5:
        word = "кейсов"
    elif remainder_10 == 1:
        word = "кейс"
    else:
        word = "кейса"
    return f"{_ru_number(count)} {word}"


def _english_case_phrase(count: int) -> str:
    return f"{_en_number(count)} {'case' if count == 1 else 'cases'}"


def build_management_report(
    *,
    period_from: date,
    period_to: date,
    queue: str | None,
    summary: dict[str, Any],
    anomaly_count: int,
    language: str = "en",
) -> tuple[dict[str, Any], str]:
    """Create a deterministic, factual English or Russian report without an LLM."""
    facts = {
        "queue": queue,
        "cases_received": summary["cases_received"],
        "cases_resolved": summary["cases_resolved"],
        "backlog_end": summary["backlog_end"],
        "sla_breaches": summary["sla_breaches"],
        "sla_breach_rate_pct": summary["sla_breach_rate_pct"],
        "throughput_to_intake_pct": summary["throughput_to_intake_pct"],
        "weighted_avg_resolution_hours": summary["weighted_avg_resolution_hours"],
        "average_daily_csat": summary["average_daily_csat"],
        "anomaly_count": anomaly_count,
        "language": language,
    }
    if language == "en":
        queue_names = {
            "kyc_review": "Customer verification (KYC)",
            "card_disputes": "Card disputes",
            "payments_support": "Payment support",
        }
        scope = f"the {queue_names.get(queue, queue)} queue" if queue else "all queues"
        net = summary["cases_received"] - summary["cases_resolved"]
        if net > 0:
            flow_summary = f"{_english_case_phrase(net)} more came in than were resolved."
        elif net < 0:
            flow_summary = f"{_english_case_phrase(abs(net))} more were resolved than came in."
        else:
            flow_summary = "Incoming and resolved volumes were equal."
        sla = (
            "SLA rate is unavailable because no cases were resolved during the period."
            if summary["sla_breach_rate_pct"] is None
            else f"Missed SLA deadlines: {_en_number(summary['sla_breach_rate_pct'], 2)}% ({_english_case_phrase(summary['sla_breaches'])})."
        )
        resolution = (
            "Average resolution time is unavailable."
            if summary["weighted_avg_resolution_hours"] is None
            else f"Weighted average resolution time: {_en_number(summary['weighted_avg_resolution_hours'], 2)} hours."
        )
        csat = (
            "CSAT is unavailable."
            if summary["average_daily_csat"] is None
            else f"Average daily CSAT: {_en_number(summary['average_daily_csat'], 2)} out of 5."
        )
        signals = "signal" if anomaly_count == 1 else "signals"
        narrative = " ".join([
            f"Northstar operations report for {period_from.isoformat()} to {period_to.isoformat()} ({scope}).",
            f"{_english_case_phrase(summary['cases_received'])} received and {_english_case_phrase(summary['cases_resolved'])} resolved; "
            f"{_english_case_phrase(summary['backlog_end'])} remained open at period end. {flow_summary}",
            sla,
            resolution,
            csat,
            f"The rule detected {anomaly_count} unusual intake {signals}.",
            "The signal marks a deviation from the recent median but does not identify its cause. "
            "This report uses calculated facts and a fixed template; no AI was used.",
        ])
        return facts, narrative

    scope = f"очередь «{queue}»" if queue else "все очереди"
    net = summary["cases_received"] - summary["cases_resolved"]
    if net > 0:
        flow_summary = f"Поступило на {_case_phrase(net)} больше, чем завершено."
    elif net < 0:
        flow_summary = f"Завершено на {_case_phrase(abs(net))} больше, чем поступило."
    else:
        flow_summary = "Поступления и завершения совпали по объёму."

    sla = (
        "SLA недоступен: за период нет завершённых кейсов."
        if summary["sla_breach_rate_pct"] is None
        else f"Нарушено сроков: {_ru_number(summary['sla_breach_rate_pct'], 2)}% ({_case_phrase(summary['sla_breaches'])})."
    )
    resolution = (
        "Среднее время решения недоступно."
        if summary["weighted_avg_resolution_hours"] is None
        else f"Среднее время решения: {_ru_number(summary['weighted_avg_resolution_hours'], 2)} ч."
    )
    csat = (
        "CSAT недоступен."
        if summary["average_daily_csat"] is None
        else f"Средняя дневная оценка CSAT: {_ru_number(summary['average_daily_csat'], 2)} из 5."
    )

    narrative = " ".join([
        f"Операционный отчёт Northstar за {period_from.isoformat()} — {period_to.isoformat()} ({scope}).",
        f"Поступило {_case_phrase(summary['cases_received'])}, завершено {_case_phrase(summary['cases_resolved'])}; "
        f"в ожидании на конец периода: {_case_phrase(summary['backlog_end'])}. {flow_summary}",
        sla,
        resolution,
        csat,
        f"Правило обнаружило {_ru_number(anomaly_count)} {_signal_word(anomaly_count)} необычного объёма поступлений.",
        "Сигнал указывает на отклонение от недавней медианы, но не устанавливает причину. "
        "Текст собран из рассчитанных KPI по шаблону; AI не использовался.",
    ])
    return facts, narrative
