from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class ImportIssue(BaseModel):
    row: int | None = None
    column: str | None = None
    code: str
    message: str


class DatasetPreview(BaseModel):
    success: bool
    filename: str
    total_rows: int
    valid_rows: int
    date_from: date | None
    date_to: date | None
    preview_rows: list[dict[str, Any]]
    errors: list[ImportIssue]


class DatasetImport(BaseModel):
    id: UUID
    name: str
    row_count: int
    date_from: date
    date_to: date
    queue_counts: dict[str, int]


class DatasetListItem(BaseModel):
    id: UUID
    name: str
    source_filename: str
    row_count: int
    date_from: date | None
    date_to: date | None


class MetricsPoint(BaseModel):
    date: date
    queue: str
    cases_received: int
    cases_resolved: int
    backlog_end: int
    avg_resolution_hours: float
    sla_breaches: int
    sla_breach_rate_pct: float | None
    reopened_cases: int
    csat_avg: float | None


class MetricsSummary(BaseModel):
    cases_received: int
    cases_resolved: int
    backlog_end: int
    sla_breaches: int
    sla_breach_rate_pct: float | None
    throughput_to_intake_pct: float | None
    weighted_avg_resolution_hours: float | None
    reopened_cases: int
    average_daily_csat: float | None


class MetricsResponse(BaseModel):
    dataset_id: UUID
    date_from: date | None
    date_to: date | None
    queue: str | None
    summary: MetricsSummary
    series: list[MetricsPoint]


class AnomalyItem(BaseModel):
    date: date
    queue: str
    metric_name: str
    actual_value: float
    baseline_median: float
    threshold_value: float
    baseline_days: int
    method: str
    severity: str
    explanation: str


class ReportCreate(BaseModel):
    period_from: date
    period_to: date
    queue: str | None = None
    language: Literal["en", "ru"] = "en"


class ReportRead(BaseModel):
    id: UUID
    dataset_id: UUID
    period_from: date
    period_to: date
    status: str
    facts: dict[str, Any]
    narrative: str
    generation_method: str
    created_at: datetime
    persisted: bool = True

    model_config = {"from_attributes": True}

