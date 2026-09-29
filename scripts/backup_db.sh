#!/usr/bin/env bash
# Database backup for the X Automation panel.
# Supports PostgreSQL (DATABASE_URL=postgresql...) and SQLite.
# Keeps the last RETENTION_DAYS backups. Schedule via cron:
#   0 3 * * *  /opt/xbot/scripts/backup_db.sh >> /var/log/xbot-backup.log 2>&1
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/xbot/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Load DATABASE_URL from .env if not already set
if [[ -z "${DATABASE_URL:-}" && -f "$(dirname "$0")/../.env" ]]; then
  export "$(grep -E '^DATABASE_URL=' "$(dirname "$0")/../.env" | xargs)"
fi
: "${DATABASE_URL:?DATABASE_URL is not set}"

if [[ "$DATABASE_URL" == postgresql* ]]; then
  OUT="$BACKUP_DIR/xbot-$STAMP.sql.gz"
  echo "Backing up PostgreSQL → $OUT"
  pg_dump "$DATABASE_URL" | gzip > "$OUT"
elif [[ "$DATABASE_URL" == sqlite* ]]; then
  SRC="${DATABASE_URL#sqlite:///}"
  OUT="$BACKUP_DIR/xbot-$STAMP.db"
  echo "Backing up SQLite ($SRC) → $OUT"
  sqlite3 "$SRC" ".backup '$OUT'"
  gzip "$OUT"
else
  echo "Unsupported DATABASE_URL scheme" >&2
  exit 1
fi

# Prune old backups
find "$BACKUP_DIR" -name 'xbot-*' -type f -mtime "+$RETENTION_DAYS" -delete
echo "Done. Retention: ${RETENTION_DAYS}d"
