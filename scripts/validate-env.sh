#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${1:-$ROOT/.env}"
missing=0

check() {
  local key="$1"
  local val
  val="$(grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '\r' || true)"
  if [[ -z "${val}" ]] || [[ "$val" == *"change-me"* ]] || [[ "$val" == *"Your"* ]] || [[ "$val" == *"yourdomain"* ]]; then
    echo "⚠️  $key not set for production"
    missing=$((missing + 1))
  else
    echo "✓ $key"
  fi
}

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE — copy from .env.production.example"
  exit 1
fi

echo "Validating $ENV_FILE ..."
check PUBLIC_API_BASE_URL
check FRONTEND_URL
check USDT_BEP20_WALLET
check ADMIN_SECRET
check TELEGRAM_BOT_TOKEN
check TELEGRAM_CHAT_ID

if [[ $missing -gt 0 ]]; then
  echo ""
  echo "$missing item(s) need production values before live revenue."
  exit 1
fi
echo "Production env looks ready."
