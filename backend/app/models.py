from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    datasets: Mapped[list["Dataset"]] = relationship(back_populates="workspace")


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="imported")
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    date_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped[Workspace] = relationship(back_populates="datasets")
    metrics: Mapped[list["DailyMetric"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")


class DailyMetric(Base):
    __tablename__ = "daily_metrics"
    __table_args__ = (
        UniqueConstraint("dataset_id", "date", "queue", name="uq_daily_metrics_dataset_date_queue"),
        CheckConstraint("cases_received >= 0", name="ck_daily_metrics_received_nonnegative"),
        CheckConstraint("cases_resolved >= 0", name="ck_daily_metrics_resolved_nonnegative"),
        CheckConstraint("backlog_end >= 0", name="ck_daily_metrics_backlog_nonnegative"),
        CheckConstraint("avg_resolution_hours >= 0", name="ck_daily_metrics_resolution_nonnegative"),
        CheckConstraint("sla_breaches >= 0", name="ck_daily_metrics_sla_nonnegative"),
        CheckConstraint("reopened_cases >= 0", name="ck_daily_metrics_reopened_nonnegative"),
        CheckConstraint("csat_avg IS NULL OR (csat_avg >= 1 AND csat_avg <= 5)", name="ck_daily_metrics_csat_range"),
        Index("ix_daily_metrics_dataset_date", "dataset_id", "date"),
        Index("ix_daily_metrics_dataset_queue_date", "dataset_id", "queue", "date"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    queue: Mapped[str] = mapped_column(String(40), nullable=False)
    cases_received: Mapped[int] = mapped_column(Integer, nullable=False)
    cases_resolved: Mapped[int] = mapped_column(Integer, nullable=False)
    backlog_end: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_resolution_hours: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    sla_breaches: Mapped[int] = mapped_column(Integer, nullable=False)
    reopened_cases: Mapped[int] = mapped_column(Integer, nullable=False)
    csat_avg: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dataset: Mapped[Dataset] = relationship(back_populates="metrics")


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    queue: Mapped[str] = mapped_column(String(40), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(80), nullable=False)
    actual_value: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    expected_min: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    expected_max: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    method: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (CheckConstraint("period_to >= period_from", name="ck_reports_period_order"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    dataset_id: Mapped[UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    period_from: Mapped[date] = mapped_column(Date, nullable=False)
    period_to: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="generated")
    facts: Mapped[dict] = mapped_column(JSONB, nullable=False)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    generation_method: Mapped[str] = mapped_column(String(30), nullable=False, default="template")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

