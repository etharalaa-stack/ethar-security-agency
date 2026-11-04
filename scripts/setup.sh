#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
mkdir -p data generated_reports

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — edit wallets & secrets."
fi

FRONT="$ROOT/frontend-cloudflare"
mkdir -p "$FRONT/assets"
API_PORT="${API_PORT:-9815}"
cat > "$FRONT/assets/config.local.js" <<EOF
window.AGENCY_API_BASE = "http://127.0.0.1:${API_PORT}/api/v1";
EOF

echo "Setup complete. Run: ./start-dev.sh"
