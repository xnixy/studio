#!/usr/bin/env bash
# Dump production (or local) Postgres using DATABASE_URL from env or backend/.env.
# Usage:
#   export DATABASE_URL=postgresql://...
#   ./scripts/backup_postgres.sh
# Output: backend/backups/studio-YYYYMMDD-HHMMSS.sql.gz

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${ROOT}/backups"
mkdir -p "$OUT_DIR"

if [[ -z "${DATABASE_URL:-}" && -f "${ROOT}/.env" ]]; then
  # shellcheck disable=SC1091
  set -a
  # shellcheck disable=SC1090
  source <(grep -E '^DATABASE_URL=' "${ROOT}/.env" | sed 's/\r$//')
  set +a
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required" >&2
  exit 1
fi

# asyncpg URLs use postgresql+asyncpg:// — pg_dump wants postgresql://
DUMP_URL="${DATABASE_URL/postgresql+asyncpg:\/\//postgresql:\/\/}"
DUMP_URL="${DUMP_URL/postgres:\/\//postgresql:\/\/}"

STAMP="$(date -u +%Y%m%d-%H%M%S)"
OUT="${OUT_DIR}/studio-${STAMP}.sql.gz"

echo "Writing ${OUT}"
pg_dump --no-owner --no-acl "$DUMP_URL" | gzip -c > "$OUT"
ls -lh "$OUT"
echo "Restore example: gunzip -c ${OUT} | psql \"\$DATABASE_URL\""
