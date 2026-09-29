#!/usr/bin/env bash
set -euo pipefail

# Running as root (first boot): take ownership of the (possibly freshly mounted)
# data volume, then re-exec this script as the unprivileged xbot user.
if [ "$(id -u)" = "0" ]; then
  mkdir -p /app/data
  chown -R xbot:xbot /app/data
  exec gosu xbot "$0" "$@"
fi

# Wait for the database (Postgres) to accept connections, then migrate.
if [[ "${DATABASE_URL:-}" == postgresql* ]]; then
  echo "Waiting for database…"
  for i in $(seq 1 30); do
    python - <<'PY' && break || sleep 2
import os, sys
from sqlalchemy import create_engine
try:
    create_engine(os.environ["DATABASE_URL"]).connect().close()
except Exception:
    sys.exit(1)
PY
  done
fi

echo "Running database migrations…"
python manage.py upgrade

exec "$@"
