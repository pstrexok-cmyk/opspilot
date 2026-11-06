# OpsPilot product roadmap

The Northstar demo is publicly hosted and uses a persistent Neon database with fictional data. The first expansion adds clear page navigation and separates existing capabilities into focused work areas. Keep the work incremental and verify each area before adding the next one.

## Proposed navigation

1. **Overview** — KPI dashboard and weekly trends.
2. **Queues** — filterable comparison of intake, resolved volume, open backlog, and SLA breaches by queue.
3. **Signals** — unusual-intake signals with severity and explanation.
4. **Recommendations** — rule-based checks grounded in KPI values, with evidence and a suggested investigation.
5. **Reports** — generate a management summary for the selected dates and queue.
6. **Data** — dataset catalogue, date coverage, and CSV analysis; local mode also supports persistent import.
7. **Metric guide** — KPI definitions, interpretation, and analytical caveats.

## Delivery sequence

1. **Done:** add page navigation and separate existing modules while retaining Overview as the landing page.
2. **Done:** add public CSV analysis without shared database writes, evidence-backed Recommendations, and a disabled-by-default optional OpenAI interpretation using aggregate KPI only. The public AI button activates after the server key is configured; a shared monthly request limit is stored in PostgreSQL.
3. Build a fictional case-level dataset and a Cases work queue with status, priority, owner, and SLA due time. Current Northstar data is daily aggregate data and cannot support honest case-level drill-down on its own.
4. Add investigation and acknowledgement states to signals after defining persistence and shared-demo safety.
5. Add report history and downloadable exports.
6. **In progress:** configure the OpenAI API project hard spend cap and the server-side secret, then verify a live AI request against the synthetic CSV.

The public demo analyzes uploaded CSVs temporarily and keeps database imports and shared-database writes disabled. Enable persistent imports only after adding authentication and per-user data isolation.

Each step should have a visible user outcome and be checked before moving on. Keep sample data fictional. Add authentication and per-user data isolation before enabling persistent imports on a public deployment.
