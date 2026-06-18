# ── Stage 1: Builder ──────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt requirements-dev.txt ./

RUN pip install --no-cache-dir --user -r requirements.txt

# ── Stage 2: Runtime ──────────────────────────────────────────
FROM python:3.12-slim

# Create non-root user
RUN groupadd -r murotech && useradd -r -g murotech -d /app -s /sbin/nologin murotech

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/murotech/.local

# Copy application code
COPY --chown=murotech:murotech . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
ENV PATH=/home/murotech/.local/bin:$PATH

EXPOSE 5001

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5001/api/v1/config', timeout=5)" || exit 1

USER murotech

CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "wsgi:application"]
