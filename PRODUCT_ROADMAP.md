# OpsPilot product roadmap

The current MVP is a working dashboard for a fictional digital bank. Hosting comes next; then the UI can grow from one dashboard into a small operations product.

## Proposed navigation

1. **Overview** — current KPI dashboard and weekly trends.
2. **Datasets** — dataset catalogue, data-quality checks, date coverage, and CSV import for a private/local workspace.
3. **Signals** — searchable anomaly inbox with severity, affected queue, explanation, and investigate/acknowledge status.
4. **Reports** — report history, detail pages, filters, and CSV/PDF export.
5. **Metric guide** — KPI definitions, formulas, caveats, and business interpretation.

## Delivery sequence after hosting

1. Add persistent page navigation and routing, retaining Overview as the landing page.
2. Build the Datasets catalogue and dataset detail view.
3. Turn anomaly cards into a triage workflow with acknowledged status and notes.
4. Add report history and downloadable exports.
5. Add a business process page that connects each KPI to operational decisions.

Each step should have a visible user outcome and be checked before moving on. Keep sample data fictional. Add authentication and per-user data isolation before enabling CSV imports on a public deployment.
