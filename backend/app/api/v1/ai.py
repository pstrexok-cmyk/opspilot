import json
import os
from datetime import date, datetime, timezone
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text

from app.database import engine


router = APIRouter(prefix="/api/v1/ai", tags=["AI analysis"])
MONTHLY_REQUEST_LIMIT = 500
MAX_OUTPUT_TOKENS = 600
MODEL = "gpt-6-luna"


class RecommendationEvidence(BaseModel):
    key: Literal["inflow_exceeds_resolved", "review_sla_breaches", "review_reopened_cases"]
    evidence: int = Field(ge=0, le=10_000_000)


class MetricsSummary(BaseModel):
    cases_received: int = Field(ge=0, le=10_000_000)
    cases_resolved: int = Field(ge=0, le=10_000_000)
    backlog_end: int = Field(ge=0, le=10_000_000)
    sla_breaches: int = Field(ge=0, le=10_000_000)
    sla_breach_rate_pct: float | None = Field(default=None, ge=0, le=100)
    throughput_to_intake_pct: float | None = Field(default=None, ge=0, le=1000)
    weighted_avg_resolution_hours: float | None = Field(default=None, ge=0, le=1_000_000)
    reopened_cases: int = Field(ge=0, le=10_000_000)
    average_daily_csat: float | None = Field(default=None, ge=1, le=5)


class AIAnalysisRequest(BaseModel):
    period_from: date
    period_to: date
    summary: MetricsSummary
    recommendations: list[RecommendationEvidence] = Field(max_length=3)
    language: Literal["en", "ru"] = "en"

    @model_validator(mode="after")
    def period_is_ordered(self) -> "AIAnalysisRequest":
        if self.period_from > self.period_to:
            raise ValueError("period_from must be on or before period_to")
        return self


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _current_usage() -> int:
    with engine.connect() as connection:
        used = connection.execute(
            text("SELECT request_count FROM ai_monthly_usage WHERE month_key = :month_key"),
            {"month_key": _month_key()},
        ).scalar_one_or_none()
    return int(used or 0)


def _reserve_request() -> int:
    """Atomically count one call before sending it to the paid API."""
    with engine.begin() as connection:
        used = connection.execute(
            text(
                """INSERT INTO ai_monthly_usage (month_key, request_count)
                   VALUES (:month_key, 1)
                   ON CONFLICT (month_key) DO UPDATE
                   SET request_count = ai_monthly_usage.request_count + 1,
                       updated_at = NOW()
                   WHERE ai_monthly_usage.request_count < :request_limit
                   RETURNING request_count"""
            ),
            {"month_key": _month_key(), "request_limit": MONTHLY_REQUEST_LIMIT},
        ).scalar_one_or_none()
    if used is None:
        raise HTTPException(status_code=429, detail="The monthly AI demo limit has been reached.")
    return int(used)


def _extract_text(response: dict) -> str:
    parts = [
        item.get("text", "")
        for output in response.get("output", [])
        if output.get("type") == "message"
        for item in output.get("content", [])
        if item.get("type") == "output_text"
    ]
    return "\n".join(part for part in parts if part).strip()


@router.get("/status")
def ai_status() -> dict[str, int | bool]:
    configured = bool(os.getenv("OPENAI_API_KEY"))
    used = _current_usage()
    return {
        "enabled": configured and used < MONTHLY_REQUEST_LIMIT,
        "configured": configured,
        "monthly_limit": MONTHLY_REQUEST_LIMIT,
        "used": used,
        "remaining": max(0, MONTHLY_REQUEST_LIMIT - used),
    }


@router.post("/analyze-upload")
def analyze_upload_with_ai(payload: AIAnalysisRequest) -> dict[str, int | str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="AI analysis is not configured yet.")

    used = _reserve_request()
    language = "Russian" if payload.language == "ru" else "English"
    instructions = (
        "You are OpsPilot, an operations analyst. Interpret only the supplied aggregate synthetic metrics. "
        "Write in " + language + ". Return a concise management note with: what stands out, what the data may "
        "suggest, and two practical questions for the operations team. Quote figures from the input accurately. "
        "Do not invent queue-level details, dates, benchmarks, or causes. Distinguish observed facts from hypotheses. "
        "This is an educational fictional dataset, not financial or regulatory advice."
    )
    body = json.dumps(
        {
            "model": MODEL,
            "instructions": instructions,
            "input": json.dumps(payload.model_dump(mode="json"), ensure_ascii=False),
            "max_output_tokens": MAX_OUTPUT_TOKENS,
        }
    ).encode("utf-8")
    request = Request(
        "https://api.openai.com/v1/responses",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read())
    except HTTPError as error:
        if error.code == 429:
            raise HTTPException(status_code=503, detail="The AI provider is temporarily rate-limited.") from error
        raise HTTPException(status_code=502, detail="The AI provider could not complete the analysis.") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=502, detail="The AI provider could not complete the analysis.") from error

    analysis = _extract_text(result)
    if not analysis:
        raise HTTPException(status_code=502, detail="The AI provider returned an empty analysis.")
    return {
        "analysis": analysis,
        "monthly_limit": MONTHLY_REQUEST_LIMIT,
        "used": used,
        "remaining": max(0, MONTHLY_REQUEST_LIMIT - used),
    }
