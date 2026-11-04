#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ -d "$ROOT/frontend-cloudflare" ]]; then
  FRONT="$ROOT/frontend-cloudflare"
else
  FRONT="$(cd "$ROOT/../frontend-cloudflare" && pwd)"
fi
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

port_in_use() {
  local p="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -tlnH "sport = :$p" 2>/dev/null | grep -q .
  else
    python3 -c "import socket; s=socket.socket(); s.settimeout(0.2); r=s.connect_ex(('127.0.0.1',$p)); s.close(); exit(0 if r==0 else 1)" 2>/dev/null
  fi
}

if port_in_use "$API_PORT"; then
  echo "ERROR: port ${API_PORT} is already in use (API may already be running)."
  echo "  Use it:  http://127.0.0.1:${API_PORT}/docs"
  echo "  Or stop: fuser -k ${API_PORT}/tcp ${FRONT_PORT}/tcp 2>/dev/null; pkill -f 'backend-engine/.venv.*uvicorn app.main' 2>/dev/null"
  echo "  Or ports: API_PORT=9816 FRONT_PORT=8789 ./start-dev.sh"
  exit 1
fi
if port_in_use "$FRONT_PORT"; then
  echo "ERROR: port ${FRONT_PORT} is already in use (frontend may already be running)."
  echo "  Use it:  http://127.0.0.1:${FRONT_PORT}/index.html"
  echo "  Or stop: fuser -k ${FRONT_PORT}/tcp 2>/dev/null"
  echo "  Or ports: FRONT_PORT=8789 ./start-dev.sh"
  exit 1
fi

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
