#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VENV="${VENV:-$ROOT/.venv}"
if [[ ! -x "$VENV/bin/uvicorn" ]]; then
  echo "Creating virtualenv at $VENV ..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -r requirements.txt
fi

mkdir -p data generated_reports
export PYTHONPATH="$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

PORT="${PORT:-9815}"
echo "API: http://127.0.0.1:${PORT}  (docs: /docs)"
exec "$VENV/bin/uvicorn" app.main:app --host 0.0.0.0 --port "$PORT" --reload
