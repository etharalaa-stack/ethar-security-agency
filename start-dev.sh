#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
FRONT="$(cd "$ROOT/../frontend-cloudflare" && pwd)"
API_PORT="${API_PORT:-9815}"
FRONT_PORT="${FRONT_PORT:-8788}"
VENV="${VENV:-$ROOT/.venv}"

mkdir -p "$ROOT/data" "$ROOT/generated_reports"

if [[ ! -x "$VENV/bin/uvicorn" ]]; then
  echo "Creating Python virtualenv…"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -r "$ROOT/requirements.txt"
fi

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

export PYTHONPATH="$ROOT"
CONFIG_JS="$FRONT/assets/config.local.js"
cat > "$CONFIG_JS" <<EOF
window.AGENCY_API_BASE = "http://127.0.0.1:${API_PORT}/api/v1";
EOF

echo "ETHAR LABS UK LTD — Enterprise v2.0 dev stack"
echo "  API:       http://127.0.0.1:${API_PORT}  (docs: /docs)"
echo "  Frontend:  http://127.0.0.1:${FRONT_PORT}/index.html"
echo "  Config:    ${CONFIG_JS}"
echo ""
echo "Press Ctrl+C to stop both services."

cleanup() {
  kill "$API_PID" "$WORKER_PID" "$FRONT_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

PORT="$API_PORT" VENV="$VENV" "$ROOT/scripts/run-api.sh" &
API_PID=$!
sleep 1
VENV="$VENV" "$ROOT/scripts/run-worker.sh" &
WORKER_PID=$!
(cd "$FRONT" && python3 -m http.server "$FRONT_PORT") &
FRONT_PID=$!

wait "$API_PID"
