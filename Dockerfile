# syntax=docker/dockerfile:1

# --------------------------------------------------------------------------
# Build stage: resolve and install dependencies into a self-contained venv.
# --------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt ./
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt

# --------------------------------------------------------------------------
# Runtime stage: the venv plus the application, running as a non-root user.
# --------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=unsdg.settings \
    DJANGO_DEBUG=False \
    DJANGO_DB_PATH=/app/var/db.sqlite3 \
    PORT=8000

RUN adduser --system --group --uid 10001 --home /app app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app . .

# staticfiles/ is written at build time; var/ holds the SQLite file Django's
# admin needs. The site's own data is read-only CSV.
RUN mkdir -p /app/staticfiles /app/var \
 && chmod +x /app/docker-entrypoint.sh \
 && chown -R app:app /app

USER app

# Collect static with a throwaway key: nothing secret is baked into the image.
RUN SECRET_KEY=collectstatic-only python manage.py collectstatic --noinput --clear

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/healthz', timeout=4).status == 200 else 1)"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
# Bare "gunicorn": the entrypoint supplies the module and the tuned flags, and
# any extra arguments here are passed through to it.
CMD ["gunicorn"]
