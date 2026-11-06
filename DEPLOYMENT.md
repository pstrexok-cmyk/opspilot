# Hosting OpsPilot

## Proposed free demo setup

- **Render Free** runs the Docker app and serves the React site and FastAPI API from the same address.
- **Neon Free** stores the seeded fictional Northstar dataset and remains available without an expiry date.
- The regular management report uses a deterministic template. Optional AI interpretation stays disabled until its API key is added.
- The public demo permits stateless CSV analysis but disables persistent imports and does not save generated reports. Uploaded files are not added to the shared demo database.

## Optional AI interpretation

The public CSV analyzer can use OpenAI's Responses API to write a short management interpretation. The browser sends only aggregate KPI values and rule keys to OpsPilot's backend; the raw CSV is not sent to OpenAI. The feature stays disabled until `OPENAI_API_KEY` is added to the Render service's protected environment settings.

The public demo has a shared application cap of 500 AI requests per UTC month, stored in PostgreSQL, and each response is limited to 600 output tokens. Also set a separate **$1 monthly hard spend limit** with enforcement enabled in the OpenAI API project's Limits settings; configure a $0.50 alert. The application request cap and provider spend cap protect different things, so use both. Never put the API key in GitHub, frontend code, or chat.

The trade-off is that a free Render service sleeps after 15 minutes without traffic. The first visit after sleep can take about a minute. Render's free PostgreSQL service is not selected because its free databases expire; Neon is a separate persistent free database option. Free quotas and provider terms can change.

## What is already prepared

`Dockerfile` builds the React UI and Python API into one service. On startup, the service applies database migrations and inserts the fictional sample data if the database is empty. `render.yaml` describes a free Frankfurt web service and prompts for the database URL as a secret. No credentials belong in Git or in this file.

## Steps to publish

1. Choose whether the GitHub source repository should be public or private. A public repo is easier for a portfolio reviewer to inspect; a private repo needs GitHub access for reviewers.
2. Create a GitHub repository and push the project source. Keep `.env` out of the repository; `.gitignore` already excludes it.
3. Create a Neon project and copy its pooled PostgreSQL connection string.
4. In Render, create a Blueprint from the GitHub repository. Enter the Neon connection string in Render's protected `DATABASE_URL` field when prompted. Do not paste it into chat, a commit, or a screenshot.
5. Wait for the first deployment to finish, then open the generated `onrender.com` URL and check the dashboard and `/api/v1/health`.

Creating accounts, choosing repository visibility, granting GitHub access, and publishing the public site must be done by the account owner. Review those exact steps before publication.

## Local build

From the project root, run `docker build -t opspilot .`. The hosted image defaults to the public demo mode. For local development, use the existing Vite + FastAPI workflow documented in `README.md`, which leaves CSV import enabled.

## Limitations

This is a portfolio demo with fictional aggregate data, not a production banking system. It has no login, user isolation, or real bank connection. CSV uploads are sent to the hosting service for temporary analysis; do not upload real customer, account, or other confidential data. Add authentication and tenant-level isolation before enabling persistent imports.
