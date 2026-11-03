#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VENV="${VENV:-$ROOT/.venv}"
if [[ ! -x "$VENV/bin/python" ]]; then
  echo "Run ./scripts/run-api.sh once first (creates .venv), or: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

mkdir -p data generated_reports
export PYTHONPATH="$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

echo "Background worker (paced desk pipeline) — STAGE_DELAY_SECONDS=${STAGE_DELAY_SECONDS:-15}"
exec "$VENV/bin/python" -m app.worker
