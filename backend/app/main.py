from pathlib import Path
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.datasets import router as datasets_router
from app.database import check_database_connection


app = FastAPI(
    title="OpsPilot API",
    description="Operations intelligence for the fictional Northstar digital bank.",
    version="0.1.0",
)
app.include_router(datasets_router)

frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@app.get("/api/v1/sample-data", include_in_schema=False)
def download_sample_data() -> FileResponse:
    sample_path = Path(__file__).resolve().parents[2] / "sample-data" / "northstar_daily_operations.csv"
    if not sample_path.is_file():
        raise HTTPException(status_code=404, detail="Generate the Northstar sample CSV first.")
    return FileResponse(sample_path, filename=sample_path.name, media_type="text/csv")


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    try:
        check_database_connection()
    except Exception as error:
        raise HTTPException(status_code=503, detail="Database is unavailable") from error
    return {"status": "ok", "database": "connected"}


if (frontend_dist / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> HTMLResponse:
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        return HTMLResponse((frontend_dist / "index.html").read_text(encoding="utf-8"))

