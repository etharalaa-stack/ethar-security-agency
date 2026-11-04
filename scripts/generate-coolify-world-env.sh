#!/usr/bin/env bash
# Writes coolify-paste.env — copy entire file into Coolify → Environment Variables
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/coolify-paste.env"
DOMAIN="${1:-${PUBLIC_DOMAIN:-}}"

if [[ -z "$DOMAIN" ]]; then
  echo "Usage: PUBLIC_DOMAIN=agency.example.com $0"
  echo "   or: $0 agency.example.com"
  exit 1
fi

DOMAIN="${DOMAIN#https://}"
DOMAIN="${DOMAIN#http://}"
DOMAIN="${DOMAIN%%/*}"
EXTRA="${EXTRA_DOMAINS:-${2:-}}"
# Comma-separated extra hostnames (e.g. www.api.etharlabs.com)
IFS=',' read -ra EXTRA_ARR <<< "${EXTRA// /}"

hosts=("$DOMAIN")
origins=("https://${DOMAIN}")
for h in "${EXTRA_ARR[@]}"; do
  [[ -z "$h" ]] && continue
  h="${h#https://}"
  h="${h#http://}"
  h="${h%%/*}"
  hosts+=("$h")
  origins+=("https://${h}")
done
TRUSTED_HOSTS="$(IFS=,; echo "${hosts[*]}")"
CORS_ORIGINS="$(IFS=,; echo "${origins[*]}")"

load() {
  grep -E "^${1}=" "$ROOT/.env" 2>/dev/null | cut -d= -f2- | tr -d '\r' || true
}

ADMIN="$(load ADMIN_SECRET)"
if [[ -z "$ADMIN" || "$ADMIN" == *change-me* || "$ADMIN" == abc123 ]]; then
  ADMIN="$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p)"
fi

BEP20="$(load USDT_BEP20_WALLET)"
TRC20="$(load USDT_TRC20_WALLET)"
BSC="$(load BSCSCAN_API_KEY)"
TRON="$(load TRON_API_KEY)"
TG_BOT="$(load TELEGRAM_BOT_TOKEN)"
TG_CHAT="$(load TELEGRAM_CHAT_ID)"

[[ -z "$BEP20" ]] && BEP20="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
[[ -z "$TRC20" ]] && TRC20="TYourTRC20WalletAddressHere"

cat >"$OUT" <<EOF
DEBUG=false
PORT=8000
PAYMENT_USDT_ONLY=true
ALLOW_TEST_PAYMENTS=false
REQUIRE_ORDER_ACCESS_TOKEN=true
RATE_LIMIT_ENABLED=true

PUBLIC_API_BASE_URL=https://${DOMAIN}
FRONTEND_URL=https://${DOMAIN}
CORS_ORIGINS=${CORS_ORIGINS}
TRUSTED_HOSTS=${TRUSTED_HOSTS}

DATABASE_URL=sqlite+aiosqlite:///./data/agency.db
DATABASE_URL_SYNC=sqlite:///./data/agency.db
STAGE_DELAY_SECONDS=3600

USDT_BEP20_WALLET=${BEP20}
USDT_TRC20_WALLET=${TRC20}
BSCSCAN_API_KEY=${BSC}
TRON_API_KEY=${TRON}

TELEGRAM_BOT_TOKEN=${TG_BOT}
TELEGRAM_CHAT_ID=${TG_CHAT}
ADMIN_SECRET=${ADMIN}

OPENROUTER_APP_TITLE=ETHAR LABS UK LTD
EOF

echo "Wrote $OUT"
echo "ADMIN_SECRET (save locally): ${ADMIN}"
echo "Next: Coolify → Environment → paste file contents → Save → Redeploy"
