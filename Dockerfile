FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_PUBLIC_DEMO=true
ENV VITE_PUBLIC_DEMO=${VITE_PUBLIC_DEMO}
RUN npm run build

FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.lock /app/backend/requirements.lock
RUN pip install --no-cache-dir -r /app/backend/requirements.lock
COPY backend/ /app/backend/
COPY sample-data/ /app/sample-data/
COPY --from=frontend-build /frontend/dist /app/frontend/dist
WORKDIR /app/backend
EXPOSE 10000
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
