FROM python:3.12-slim

# Runtime deps for psycopg2 / curl_cffi / argon2 are shipped as wheels, but a
# few system libs are still needed at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 curl ca-certificates gosu \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root user. The container starts as root only so the entrypoint can fix
# ownership of a freshly-mounted volume, then drops to `xbot` via gosu.
RUN useradd --create-home --uid 10001 xbot \
    && mkdir -p /app/data \
    && chown -R xbot:xbot /app

EXPOSE 5000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "-c", "gunicorn.conf.py", "run:app"]
