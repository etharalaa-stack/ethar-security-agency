# ETHAR LABS UK LTD — USDT-only global launch (no Stripe)

Company No. **17032523** · Settlement: **USDT BEP20 + TRC20** only.

---

## Coolify Environment (copy)

```env
PAYMENT_USDT_ONLY=true
ALLOW_TEST_PAYMENTS=false
DEBUG=false
REQUIRE_ORDER_ACCESS_TOKEN=true

USDT_BEP20_WALLET=0xYourWallet
USDT_TRC20_WALLET=TYourTronWallet
BSCSCAN_API_KEY=your_key
TRON_API_KEY=optional

FRONTEND_URL=https://yourdomain.com
PUBLIC_API_BASE_URL=https://yourdomain.com
CORS_ORIGINS=https://yourdomain.com
TRUSTED_HOSTS=yourdomain.com

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
ADMIN_SECRET=
STAGE_DELAY_SECONDS=3600
```

**Do not set** `STRIPE_WEBHOOK_SECRET` — endpoint returns 404.

---

## Client flow

1. Choose **USDT BEP20** or **USDT TRC20**
2. Send **exact USD total** as USDT (1:1) to agency wallet
3. Paste **TxHash** → Submit
4. Open **track URL with `token=`** → milestones if applicable → PDF

---

## Validate before go-live

```bash
./scripts/validate-env.sh
```

---

## Edge protection

See [`deploy/CLOUDFLARE-WAF.md`](deploy/CLOUDFLARE-WAF.md)

---

## Deploy

```bash
git push origin main
```

Coolify → **Redeploy** (rebuild `web`, `api`, `worker`).
