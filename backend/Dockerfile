# API and worker image. Build from the repository root:
#   docker build -f backend/Dockerfile -t ledgerlens-backend .
# CPU only; no model weights or datasets are copied in. OCR models ship inside the rapidocr wheel.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

RUN pip install --no-cache-dir uv==0.11.29

WORKDIR /app/backend
# Dependencies first, so code changes do not reinstall them.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --extra ocr --no-install-project

COPY backend/ ./
RUN uv sync --frozen --no-dev --extra ocr

# Committed evaluation results, served read-only by /evaluation/report.
COPY evals/results /app/evals/results

RUN useradd --uid 10001 --create-home app \
    && mkdir -p /data/storage /data/llm-cache \
    && chown -R app /data
USER app

ENV PATH=/app/backend/.venv/bin:$PATH \
    LEDGERLENS_STORAGE_DIR=/data/storage \
    LEDGERLENS_LLM_CACHE_DIR=/data/llm-cache \
    LEDGERLENS_RESULTS_DIR=/app/evals/results

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn ledgerlens.api.app:create_app --factory --host 0.0.0.0 --port 8000"]
