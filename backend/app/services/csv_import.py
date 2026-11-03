from dataclasses import dataclass
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_ROWS = 100_000
ALLOWED_QUEUES = {"kyc_review", "card_disputes", "payments_support"}
REQUIRED_COLUMNS = {
    "date",
    "queue",
    "cases_received",
    "cases_resolved",
    "backlog_end",
    "avg_resolution_hours",
    "sla_breaches",
    "reopened_cases",
    "csat_avg",
}
INTEGER_COLUMNS = {
    "cases_received",
    "cases_resolved",
    "backlog_end",
    "sla_breaches",
    "reopened_cases",
}
NUMERIC_COLUMNS = INTEGER_COLUMNS | {"avg_resolution_hours", "csat_avg"}


@dataclass
class CSVValidation:
    filename: str
    total_rows: int
    records: list[dict[str, Any]]
    preview_rows: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    date_from: date | None
    date_to: date | None

    @property
    def success(self) -> bool:
        return not self.errors and bool(self.records)


def _issue(row: int | None, column: str | None, code: str, message: str) -> dict[str, Any]:
    return {"row": row, "column": column, "code": code, "message": message}


def validate_csv(content: bytes, filename: str | None) -> CSVValidation:
    safe_filename = Path(filename or "upload.csv").name
    issues: list[dict[str, Any]] = []

    if not safe_filename.lower().endswith(".csv"):
        issues.append(_issue(None, None, "invalid_file_type", "Upload a .csv file."))
    if not content:
        issues.append(_issue(None, None, "empty_file", "The file is empty."))
    if len(content) > MAX_UPLOAD_BYTES:
        issues.append(_issue(None, None, "file_too_large", "The file must be 10 MB or smaller."))
    if issues:
        return CSVValidation(safe_filename, 0, [], [], issues, None, None)

    try:
        frame = pd.read_csv(BytesIO(content))
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
        issue = _issue(None, None, "unreadable_csv", "The file could not be read as a UTF-8 CSV.")
        return CSVValidation(safe_filename, 0, [], [], [issue], None, None)

    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        issues.extend(_issue(None, column, "missing_column", f"Required column '{column}' is missing.") for column in missing)
        return CSVValidation(safe_filename, len(frame), [], [], issues[:100], None, None)
    if frame.empty:
        issue = _issue(None, None, "no_rows", "The CSV has a header but no data rows.")
        return CSVValidation(safe_filename, 0, [], [], [issue], None, None)
    if len(frame) > MAX_ROWS:
        issue = _issue(None, None, "too_many_rows", f"The file must contain {MAX_ROWS:,} rows or fewer.")
        return CSVValidation(safe_filename, len(frame), [], [], [issue], None, None)

    frame["date_parsed"] = pd.to_datetime(frame["date"], format="%Y-%m-%d", errors="coerce")
    frame["queue_clean"] = frame["queue"].astype("string").str.strip()
    for column in NUMERIC_COLUMNS:
        frame[f"{column}_parsed"] = pd.to_numeric(frame[column], errors="coerce")

    records: list[dict[str, Any]] = []
    preview_rows: list[dict[str, Any]] = []
    seen: dict[tuple[date, str], int] = {}

    for index, row in frame.iterrows():
        line = int(index) + 2  # CSV row 1 is the header.
        row_errors: list[dict[str, Any]] = []

        parsed_date = row["date_parsed"]
        if pd.isna(parsed_date):
            row_errors.append(_issue(line, "date", "invalid_date", "Use a real date in YYYY-MM-DD format."))
        queue = row["queue_clean"]
        if pd.isna(queue) or queue not in ALLOWED_QUEUES:
            row_errors.append(_issue(line, "queue", "invalid_queue", "Choose kyc_review, card_disputes, or payments_support."))

        values: dict[str, int | float | None] = {}
        for column in NUMERIC_COLUMNS:
            raw = row[column]
            parsed = row[f"{column}_parsed"]
            is_blank = pd.isna(raw) or (isinstance(raw, str) and not raw.strip())
            if column == "csat_avg" and is_blank:
                values[column] = None
                continue
            if pd.isna(parsed):
                row_errors.append(_issue(line, column, "invalid_number", f"'{column}' must contain a number."))
                continue
            number = float(parsed)
            if column in INTEGER_COLUMNS and not number.is_integer():
                row_errors.append(_issue(line, column, "not_integer", f"'{column}' must be a whole number."))
                continue
            if number < 0 and column != "csat_avg":
                row_errors.append(_issue(line, column, "negative_value", f"'{column}' cannot be negative."))
            if column == "csat_avg" and not 1 <= number <= 5:
                row_errors.append(_issue(line, column, "csat_out_of_range", "'csat_avg' must be between 1 and 5, or blank."))
            values[column] = int(number) if column in INTEGER_COLUMNS else number

        if values.get("sla_breaches") is not None and values.get("cases_resolved") is not None:
            if values["sla_breaches"] > values["cases_resolved"]:
                row_errors.append(_issue(line, "sla_breaches", "sla_exceeds_resolved", "SLA breaches cannot exceed cases resolved."))

        if not pd.isna(parsed_date) and not pd.isna(queue) and queue in ALLOWED_QUEUES:
            business_date = parsed_date.date()
            key = (business_date, str(queue))
            if key in seen:
                row_errors.append(_issue(line, "date", "duplicate_date_queue", f"This date and queue already appear on row {seen[key]}."))
            else:
                seen[key] = line

        if row_errors:
            issues.extend(row_errors)
            continue

        record = {
            "date": parsed_date.date(),
            "queue": str(queue),
            **values,
        }
        records.append(record)
        if len(preview_rows) < 5:
            preview_rows.append({**record, "date": record["date"].isoformat()})

    if len(issues) > 100:
        issues = issues[:100] + [_issue(None, None, "errors_truncated", "Only the first 100 validation errors are shown.")]

    dates = [record["date"] for record in records]
    return CSVValidation(
        filename=safe_filename,
        total_rows=len(frame),
        records=records,
        preview_rows=preview_rows,
        errors=issues,
        date_from=min(dates) if dates else None,
        date_to=max(dates) if dates else None,
    )

