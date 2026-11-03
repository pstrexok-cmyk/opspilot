# OpsPilot

An operations intelligence portfolio project for the fictional Northstar digital bank.

See [`PORTFOLIO_DEMO.md`](PORTFOLIO_DEMO.md) for the business question, three-minute demo flow, architecture, metric definitions, limitations, and an honest CV description.

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for the proposed free hosting setup and publishing steps. [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md) outlines the next step from the current single-page MVP to a multi-page operations product.

## Local development

1. In this folder, copy `.env.example` to `.env`.
2. Start PostgreSQL with `docker compose up -d db` (port `5433` on your Mac; inside Docker it remains `5432`).
3. In `backend/`, create and activate a virtual environment with `python3 -m venv .venv` and `source .venv/bin/activate`.
4. Install the API and its learning checks with `pip install -e '.[test]'`, then run `uvicorn app.main:app --reload --reload-dir app --env-file ../.env`.
5. In another terminal, from `backend/`, run `alembic upgrade head` once to create/update the database tables, then `python -m app.seed` to add the demo workspace.
6. From `backend/`, run `python -m app.generate_sample` to create the 90-day fictional Northstar CSV in `sample-data/`.
7. In a second terminal, open `frontend/`, run `npm ci`, then `npm run dev`.
8. Open [http://127.0.0.1:5173/](http://127.0.0.1:5173/) for the OpsPilot dashboard.

The dashboard starts with the synthetic Northstar sample. Choose a queue and dates, then click **Show results** (`Показать`) to update KPI cards and weekly charts. The **How should I read these metrics?** (`Как читать показатели?`) section explains the formulas. To try another file, open **Upload another CSV** (`Загрузить другой CSV`), download the sample template, choose a CSV, preview its validation result, and import it only after it passes.

The interface opens in English. Use the **EN / RU** control in the top bar to switch the full dashboard, charts, anomaly explanations, CSV guidance, and management report to Russian. The choice is remembered in the browser.

For developer/API inspection, open `http://127.0.0.1:8000/docs`. `POST /api/v1/datasets/preview` checks a file without saving it. `POST /api/v1/datasets` imports a validated CSV; `GET /api/v1/datasets` lists saved datasets; and `GET /api/v1/datasets/{id}/metrics` returns the KPI summary and daily series. The metrics endpoint accepts `from`, `to`, and `queue` filters.

The SLA breach percentage is `SLA breaches / resolved cases`. Throughput-to-intake is `resolved cases / incoming cases`; it compares flows, not the same cohort of cases. Average resolution time is weighted by resolved volume. The daily CSAT average is currently unweighted because the sample does not include survey counts.

Daily intake spikes are flagged when intake exceeds 1.5 times the median of available observations in the previous 28 calendar days; at least 14 observations are required. A stronger label means the actual value is at least twice the baseline median. The signal identifies unusual volume, not its cause. Management reports use a deterministic template built from calculated KPI and anomaly counts, so no LLM key or usage cost is required.

Run the backend checks from `backend/` with `pytest`.

To stop the database, run `docker compose down` from this folder. Docker keeps its named volume and local data; `docker compose down -v` removes that volume and its data.

All example business data will be synthetic. Never use real customer or account information.

