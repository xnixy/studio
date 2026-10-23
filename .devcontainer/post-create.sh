#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Backend: Python venv + dependencies"
cd "$ROOT/backend"
python -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
mkdir -p media

echo "==> Frontend: npm install"
cd "$ROOT/frontend"
if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi

echo "==> Dev container ready."
echo "    API:      cd backend && source .venv/bin/activate && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 3001 --reload"
echo "    Frontend: cd frontend && npm run dev"
echo "    Worker:   cd backend && source .venv/bin/activate && python -m app.render_worker --poll-seconds 5"
