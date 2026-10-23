#!/usr/bin/env bash
# Runs each time the container starts (after create, and on reopen).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -x "$ROOT/backend/.venv/bin/python" ]]; then
  cd "$ROOT/backend"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  # Wait briefly for Postgres health (compose already depends_on healthy).
  for _ in $(seq 1 30); do
    if python -c "import socket; s=socket.create_connection(('postgres', 5432), 2); s.close()" 2>/dev/null; then
      break
    fi
    sleep 1
  done
  alembic upgrade head || echo "warning: alembic upgrade failed (DB may still be starting)"
fi
