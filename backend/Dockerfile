# Build context: repository root (see docker-compose.yml)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PROMPTS_DIR=/app/prompts \
    DATABASE_URL=sqlite:////app/data/mate.db \
    DECISION_LOG_PATH=/app/data/decision_log.json \
    ARTIFACTS_DIR=/app/data/artifacts

# Node.js runs the generated MVP's tests (fixed command, no model-generated shell).
RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY prompts ./prompts
COPY scripts ./scripts

RUN useradd --create-home --uid 10001 mate && mkdir -p /app/data && chown -R mate /app/data
USER mate

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=12 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2).status == 200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
