# syntax=docker/dockerfile:1.6
#
# Fynd AR Receivables Insights — Boltic serverless image.
#
# 1. Install Flask + gunicorn.
# 2. Bake the static dashboard HTML at build time via build_v4.py
#    (embeds ./data3.json into window.__AR_DATA__).
# 3. Serve the resulting HTML with gunicorn on $PORT (default 8080).

FROM python:3.11-slim AS base

# gunicorn behaves better when Python doesn't buffer stdout/stderr.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    AR_OUT_DIR=/app/build \
    PORT=8080

WORKDIR /app

# Install runtime deps first (better layer caching).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source (build scripts, data snapshot, Flask app).
COPY build_v4.py app.py data3.json ./

# Bake the dashboard HTML (~4 MB with data embedded).
RUN python build_v4.py \
 && ls -lh /app/build

EXPOSE 8080

# 1 worker is fine — the app just serves a single static file.
# Threaded worker keeps the /health probe responsive during large sends.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 4 --timeout 60 --access-logfile - app:app"]
