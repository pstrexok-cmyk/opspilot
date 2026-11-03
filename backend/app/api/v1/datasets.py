from collections import Counter
from pathlib import Path

from datetime import date, timedelta
from datetime import datetime, timezone
import os
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import engine
from app.models import DailyMetric, Dataset, Report, Workspace
from app.schemas import (
    AnomalyItem,
    DatasetImport,
    DatasetListItem,
    DatasetPreview,
    MetricsResponse,
    ReportCreate,
    ReportRead,
)
from app.services.anomalies import detect_intake_spikes
from app.services.csv_import import validate_csv
from app.services.kpis import calculate_kpis
from app.services.reports import build_management_report


router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetListItem])
def list_datasets() -> list[DatasetListItem]:
    with Session(engine) as session:
        datasets = session.scalars(select(Dataset).order_by(Dataset.created_at.desc())).all()
        return [
            DatasetListItem(
                id=item.id,
                name=item.name,
                source_filename=item.source_filename,
                row_count=item.row_count,
                date_from=item.date_from,
                date_to=item.date_to,
            )
            for item in datasets
        ]


@router.get("/{dataset_id}/metrics", response_model=MetricsResponse)
def get_dataset_metrics(
    dataset_id: UUID,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    queue: Literal["kyc_review", "card_disputes", "payments_support"] | None = None,
) -> MetricsResponse:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="'from' must be on or before 'to'.")

    with Session(engine) as session:
        dataset = session.get(Dataset, dataset_id)
        if dataset is None:
            raise HTTPException(status_code=404, detail="Dataset not found.")

        filters = [DailyMetric.dataset_id == dataset_id]
        if date_from:
            filters.append(DailyMetric.date >= date_from)
        if date_to:
            filters.append(DailyMetric.date <= date_to)
        if queue:
            filters.append(DailyMetric.queue == queue)

        rows = session.scalars(
            select(DailyMetric).where(*filters).order_by(DailyMetric.date, DailyMetric.queue)
        ).all()
        summary, series = calculate_kpis(rows)
        dates = [row.date for row in rows]
        return MetricsResponse(
            dataset_id=dataset_id,
            date_from=min(dates) if dates else date_from,
            date_to=max(dates) if dates else date_to,
            queue=queue,
            summary=summary,
            series=series,
        )


@router.get("/{dataset_id}/anomalies", response_model=list[AnomalyItem])
def get_dataset_anomalies(
    dataset_id: UUID,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    queue: Literal["kyc_review", "card_disputes", "payments_support"] | None = None,
) -> list[AnomalyItem]:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="'from' must be on or before 'to'.")

    with Session(engine) as session:
        if session.get(Dataset, dataset_id) is None:
            raise HTTPException(status_code=404, detail="Dataset not found.")

        filters = [DailyMetric.dataset_id == dataset_id]
        if date_from:
            filters.append(DailyMetric.date >= date_from - timedelta(days=28))
        if date_to:
            filters.append(DailyMetric.date <= date_to)
        if queue:
            filters.append(DailyMetric.queue == queue)
        rows = session.scalars(
            select(DailyMetric).where(*filters).order_by(DailyMetric.date, DailyMetric.queue)
        ).all()
        alerts = detect_intake_spikes(rows)
        return [
            AnomalyItem(**alert)
            for alert in alerts
            if (date_from is None or alert["date"] >= date_from)
            and (date_to is None or alert["date"] <= date_to)
        ]


@router.post("/{dataset_id}/reports", response_model=ReportRead, status_code=201)
def create_dataset_report(dataset_id: UUID, request: ReportCreate) -> ReportRead:
    if request.period_from > request.period_to:
        raise HTTPException(status_code=422, detail="period_from must be on or before period_to.")

    with Session(engine) as session:
        if session.get(Dataset, dataset_id) is None:
            raise HTTPException(status_code=404, detail="Dataset not found.")

        filters = [
            DailyMetric.dataset_id == dataset_id,
            DailyMetric.date >= request.period_from,
            DailyMetric.date <= request.period_to,
        ]
        if request.queue:
            filters.append(DailyMetric.queue == request.queue)
        rows = session.scalars(
            select(DailyMetric).where(*filters).order_by(DailyMetric.date, DailyMetric.queue)
        ).all()
        if not rows:
            raise HTTPException(status_code=422, detail="No data exists in the selected report period.")

        summary, _ = calculate_kpis(rows)
        history_filters = [
            DailyMetric.dataset_id == dataset_id,
            DailyMetric.date >= request.period_from - timedelta(days=28),
            DailyMetric.date <= request.period_to,
        ]
        if request.queue:
            history_filters.append(DailyMetric.queue == request.queue)
        history = session.scalars(select(DailyMetric).where(*history_filters)).all()
        anomaly_count = sum(
            1 for alert in detect_intake_spikes(history)
            if request.period_from <= alert["date"] <= request.period_to
        )
        facts, narrative = build_management_report(
            period_from=request.period_from,
            period_to=request.period_to,
            queue=request.queue,
            summary=summary,
            anomaly_count=anomaly_count,
            language=request.language,
        )
        if os.getenv("OPSPILOT_PUBLIC_DEMO", "false").lower() == "true":
            return ReportRead(
                id=uuid4(), dataset_id=dataset_id, period_from=request.period_from,
                period_to=request.period_to, status="generated", facts=facts,
                narrative=narrative, generation_method="template",
                created_at=datetime.now(timezone.utc), persisted=False,
            )
        report = Report(
            dataset_id=dataset_id,
            period_from=request.period_from,
            period_to=request.period_to,
            status="generated",
            facts=facts,
            narrative=narrative,
            generation_method="template",
        )
        session.add(report)
        session.commit()
        session.refresh(report)
        return ReportRead.model_validate(report)


@router.get("/{dataset_id}/reports", response_model=list[ReportRead])
def list_dataset_reports(
    dataset_id: UUID,
    language: Literal["en", "ru"] = Query(default="en"),
) -> list[ReportRead]:
    with Session(engine) as session:
        if session.get(Dataset, dataset_id) is None:
            raise HTTPException(status_code=404, detail="Dataset not found.")
        reports = session.scalars(
            select(Report).where(Report.dataset_id == dataset_id).order_by(Report.created_at.desc())
        ).all()
        localized: list[ReportRead] = []
        for report in reports:
            facts = report.facts
            summary = {
                key: facts.get(key)
                for key in (
                    "cases_received", "cases_resolved", "backlog_end", "sla_breaches",
                    "sla_breach_rate_pct", "throughput_to_intake_pct",
                    "weighted_avg_resolution_hours", "average_daily_csat",
                )
            }
            _, narrative = build_management_report(
                period_from=report.period_from,
                period_to=report.period_to,
                queue=facts.get("queue"),
                summary=summary,
                anomaly_count=facts.get("anomaly_count", 0),
                language=language,
            )
            localized.append(ReportRead.model_validate(report).model_copy(update={"narrative": narrative}))
        return localized


@router.post("/preview", response_model=DatasetPreview)
def preview_dataset(file: UploadFile = File(...)) -> DatasetPreview:
    if os.getenv("OPSPILOT_PUBLIC_DEMO", "false").lower() == "true":
        raise HTTPException(status_code=403, detail="CSV uploads are disabled in the shared public demo.")
    validation = validate_csv(file.file.read(10 * 1024 * 1024 + 1), file.filename)
    return DatasetPreview(
        success=validation.success,
        filename=validation.filename,
        total_rows=validation.total_rows,
        valid_rows=len(validation.records),
        date_from=validation.date_from,
        date_to=validation.date_to,
        preview_rows=validation.preview_rows,
        errors=validation.errors,
    )


@router.post("", response_model=DatasetImport, status_code=201)
def import_dataset(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
) -> DatasetImport:
    if os.getenv("OPSPILOT_PUBLIC_DEMO", "false").lower() == "true":
        raise HTTPException(status_code=403, detail="CSV uploads are disabled in the shared public demo.")
    validation = validate_csv(file.file.read(10 * 1024 * 1024 + 1), file.filename)
    if not validation.success:
        raise HTTPException(
            status_code=422,
            detail={"message": "CSV validation failed; no rows were imported.", "errors": validation.errors},
        )

    dataset_name = (name or Path(validation.filename).stem).strip()[:200]
    if not dataset_name:
        raise HTTPException(status_code=422, detail="Dataset name cannot be blank.")

    with Session(engine) as session:
        try:
            with session.begin():
                workspace = session.scalar(
                    select(Workspace).where(Workspace.name == "Northstar Digital Bank")
                )
                if workspace is None:
                    raise HTTPException(status_code=409, detail="Run the demo seed before importing data.")

                dataset = Dataset(
                    workspace_id=workspace.id,
                    name=dataset_name,
                    source_filename=validation.filename,
                    status="imported",
                    row_count=len(validation.records),
                    date_from=validation.date_from,
                    date_to=validation.date_to,
                )
                session.add(dataset)
                session.flush()
                session.add_all(
                    DailyMetric(dataset_id=dataset.id, **record)
                    for record in validation.records
                )
        except IntegrityError as error:
            raise HTTPException(status_code=409, detail="The dataset could not be saved because a row conflicts with existing data.") from error

        return DatasetImport(
            id=dataset.id,
            name=dataset.name,
            row_count=dataset.row_count,
            date_from=dataset.date_from,
            date_to=dataset.date_to,
            queue_counts=dict(Counter(record["queue"] for record in validation.records)),
        )

