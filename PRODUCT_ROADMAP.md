# OpsPilot product roadmap

The Northstar demo is publicly hosted and uses a persistent Neon database with fictional data. The first expansion adds clear page navigation and separates existing capabilities into focused work areas. Keep the work incremental and verify each area before adding the next one.

## Proposed navigation

1. **Overview** — KPI dashboard and weekly trends.
2. **Queues** — filterable comparison of intake, resolved volume, open backlog, and SLA breaches by queue.
3. **Signals** — unusual-intake signals with severity and explanation.
4. **Reports** — generate a management summary for the selected dates and queue.
5. **Data** — dataset catalogue, date coverage, and CSV import in local/private mode.
6. **Metric guide** — KPI definitions, interpretation, and analytical caveats.

## Delivery sequence

1. **In progress:** add page navigation and separate existing modules while retaining Overview as the landing page.
2. Build a fictional case-level dataset and a Cases work queue with status, priority, owner, and SLA due time. Current Northstar data is daily aggregate data and cannot support honest case-level drill-down on its own.
3. Add investigation and acknowledgement states to signals after defining persistence and shared-demo safety.
4. Add report history and downloadable exports.
5. Connect each KPI to operational decisions and responsible escalation steps.

The public demo keeps CSV import and shared-database writes disabled. Enable write features only after adding authentication and per-user data isolation.

Each step should have a visible user outcome and be checked before moving on. Keep sample data fictional. Add authentication and per-user data isolation before enabling CSV imports on a public deployment.
