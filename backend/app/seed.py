from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine
from app.models import DailyMetric, Dataset, Workspace
from app.services.csv_import import validate_csv


def seed_demo_workspace() -> Workspace:
    """Create the fictional bank's workspace once; repeated runs are safe."""
    with Session(engine) as session:
        workspace = session.scalar(select(Workspace).where(Workspace.name == "Northstar Digital Bank"))
        if workspace is None:
            workspace = Workspace(name="Northstar Digital Bank")
            session.add(workspace)
            session.commit()
            session.refresh(workspace)
        return workspace


def seed_demo_dataset() -> None:
    """Load the fictional portfolio dataset once on a fresh hosted database."""
    sample_path = Path(__file__).resolve().parents[2] / "sample-data" / "northstar_daily_operations.csv"
    if not sample_path.is_file():
        raise FileNotFoundError(f"Missing demo CSV: {sample_path}")
    validation = validate_csv(sample_path.read_bytes(), sample_path.name)
    if not validation.success:
        raise ValueError("The bundled Northstar demo CSV failed validation")

    with Session(engine) as session:
        if session.scalar(select(Dataset.id).where(Dataset.source_filename == sample_path.name)):
            return
        workspace = session.scalar(select(Workspace).where(Workspace.name == "Northstar Digital Bank"))
        if workspace is None:
            raise RuntimeError("Seed the demo workspace before its dataset")
        dataset = Dataset(
            workspace_id=workspace.id,
            name="Northstar — 90-day operations",
            source_filename=sample_path.name,
            status="imported",
            row_count=len(validation.records),
            date_from=validation.date_from,
            date_to=validation.date_to,
        )
        session.add(dataset)
        session.flush()
        session.add_all(DailyMetric(dataset_id=dataset.id, **row) for row in validation.records)
        session.commit()


if __name__ == "__main__":
    workspace = seed_demo_workspace()
    seed_demo_dataset()
    print(f"Demo workspace ready: {workspace.name} ({workspace.id})")

