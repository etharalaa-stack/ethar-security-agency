#!/usr/bin/env bash
# One-shot local install (copy/paste friendly)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== ETHAR LABS UK LTD — install-all =="

if ! command -v python3 >/dev/null; then
  echo "Install python3 first: sudo apt install python3-venv python3-pip"
  exit 1
fi

chmod +x "$ROOT/scripts/"*.sh "$ROOT/start-dev.sh" 2>/dev/null || true
"$ROOT/scripts/setup.sh"
"$ROOT/scripts/sync-frontend.sh"

if [[ ! -f "$ROOT/.env" ]]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
fi

if grep -q 'ADMIN_SECRET=change-me-in-production' "$ROOT/.env" 2>/dev/null; then
  SEC="$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p)"
  sed -i "s/ADMIN_SECRET=change-me-in-production/ADMIN_SECRET=${SEC}/" "$ROOT/.env"
  echo "Generated ADMIN_SECRET in .env"
fi

API_PORT="${API_PORT:-9815}"
FRONT="$ROOT/frontend-cloudflare"
mkdir -p "$FRONT/assets"
cat > "$FRONT/assets/config.local.js" <<EOF
window.AGENCY_API_BASE = "http://127.0.0.1:${API_PORT}/api/v1";
EOF

echo ""
echo "Done. Start platform:"
echo "  cd \"$ROOT\""
echo "  API_PORT=${API_PORT} ./start-dev.sh"
