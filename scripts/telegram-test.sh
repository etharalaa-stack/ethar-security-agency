#!/usr/bin/env bash
# Send an English-only deployment ping via @EtharSecurityBot.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOKEN="$(grep -E '^TELEGRAM_BOT_TOKEN=' "$ROOT/.env" 2>/dev/null | cut -d= -f2- | tr -d '\r' || true)"
CHAT="$(grep -E '^TELEGRAM_CHAT_ID=' "$ROOT/.env" 2>/dev/null | cut -d= -f2- | tr -d '\r' || true)"
if [[ -z "$TOKEN" || -z "$CHAT" ]]; then
  echo "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env"
  exit 1
fi
MSG="${1:-ETHAR LABS UK LTD — Telegram alerts are active. Platform notifications are English-only.}"
python3 - "$TOKEN" "$CHAT" "$MSG" <<'PY'
import json, sys, urllib.request
token, chat, text = sys.argv[1:4]
payload = json.dumps({"chat_id": chat, "text": text, "disable_web_page_preview": True}).encode()
req = urllib.request.Request(
    f"https://api.telegram.org/bot{token}/sendMessage",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=20) as resp:
    print(resp.read().decode())
PY
echo "Telegram test sent."
