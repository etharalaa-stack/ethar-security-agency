#!/usr/bin/env bash
# After you send /start to @EtharSecurityBot, run this to print TELEGRAM_CHAT_ID.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOKEN="$(grep -E '^TELEGRAM_BOT_TOKEN=' "$ROOT/.env" 2>/dev/null | cut -d= -f2- | tr -d '\r' || true)"
if [[ -z "$TOKEN" ]]; then
  echo "Set TELEGRAM_BOT_TOKEN in .env first."
  exit 1
fi
echo "Send /start to @EtharSecurityBot, then press Enter…"
read -r _
curl -sS "https://api.telegram.org/bot${TOKEN}/getUpdates" |
  python3 -c "
import json, sys
data = json.load(sys.stdin)
for u in data.get('result', []):
    m = u.get('message') or u.get('edited_message') or {}
    chat = m.get('chat') or {}
    cid = chat.get('id')
    if cid:
        print(f\"TELEGRAM_CHAT_ID={cid}  # {chat.get('first_name','')} @{chat.get('username','')}\")
"
