#!/usr/bin/env bash
# Interactive-ish production .env generator (copy/paste prompts)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/.env"
TEMPLATE="$ROOT/.env.production.example"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "Missing $TEMPLATE"
  exit 1
fi

read -r -p "API public URL (https://api.yourdomain.com): " API_URL
read -r -p "Frontend URL (https://yourdomain.com): " FRONT_URL
read -r -p "USDT BEP20 wallet: " BEP
read -r -p "USDT TRC20 wallet: " TRC
read -r -p "BSCScan API key: " BSC
read -r -p "Telegram bot token: " TG_BOT
read -r -p "Telegram chat id: " TG_CHAT
read -r -p "OpenAI/OpenRouter API key (optional): " LLM_KEY

ADMIN_SECRET="$(openssl rand -hex 32 2>/dev/null || echo "change-me-$(date +%s)")"

cp "$TEMPLATE" "$OUT"
sed -i "s|https://api.yourdomain.com|${API_URL}|g" "$OUT"
sed -i "s|https://yourdomain.com|${FRONT_URL}|g" "$OUT"
sed -i "s|0xYourBEP20Wallet|${BEP}|g" "$OUT"
sed -i "s|TYourTRC20Wallet|${TRC}|g" "$OUT"
sed -i "s|your_bscscan_key|${BSC}|g" "$OUT"
sed -i "s|use-openssl-rand-hex-32|${ADMIN_SECRET}|g" "$OUT"

grep -q "^TELEGRAM_BOT_TOKEN=$" "$OUT" && sed -i "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=${TG_BOT}|" "$OUT"
grep -q "^TELEGRAM_CHAT_ID=$" "$OUT" && sed -i "s|^TELEGRAM_CHAT_ID=.*|TELEGRAM_CHAT_ID=${TG_CHAT}|" "$OUT"
if [[ -n "$LLM_KEY" ]]; then
  sed -i "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=${LLM_KEY}|" "$OUT"
fi

echo "Wrote $OUT"
echo "ADMIN_SECRET=$ADMIN_SECRET"
"$ROOT/scripts/validate-env.sh" "$OUT" || true
