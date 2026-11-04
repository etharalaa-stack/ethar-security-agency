# إمكانيات المدفوع — ETHAR LABS UK LTD

## طرق الدفع

| الطريقة | للعميل | التحقق على السيرفر |
|---------|--------|---------------------|
| **USDT BEP20** | يرسل USDT لمحفظتك + TxHash | BscScan receipt + عقد USDT + المبلغ |
| **USDT TRC20** | يرسل USDT + TxHash | TronGrid events + المحفظة + المبلغ |
| **USDT BEP20 / TRC20** | **الإنتاج** | TxHash + تحقق مبلغ ومحفظة |
| **Card / test ref** | dev فقط | `ALLOW_TEST_PAYMENTS=true` مع `PAYMENT_USDT_ONLY` |
| **Stripe** | **معطّل** | `PAYMENT_USDT_ONLY=true` (افتراضي) |

## خطط الدفع

- **Full upfront** — 100% قبل بدء المكاتب (SLA 24h).
- **Milestones** — للطلبات **> $150**: 40% / 40% / 20%؛ الـ worker يتوقف عند `AWAITING_PAYMENT` حتى دفع المرحلة التالية عبر `track.html`.

## Coolify — Environment للمدفوع الحقيقي

```env
DEBUG=false
ALLOW_TEST_PAYMENTS=false

USDT_BEP20_WALLET=0xYourRealWallet
USDT_TRC20_WALLET=TYourRealTronWallet
BSCSCAN_API_KEY=your_key
TRON_API_KEY=optional_trongrid_pro

STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_TEST_REFERENCE_PREFIX=STRIPE-TEST-

PAYMENT_AMOUNT_TOLERANCE_USD=1.0
```

## USDT-only launch doc

See [`USDT-ONLY-LAUNCH.md`](USDT-ONLY-LAUNCH.md) and [`deploy/CLOUDFLARE-WAF.md`](deploy/CLOUDFLARE-WAF.md).

## Telegram + PDF

- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` — تنبيه دفع + رابط موافقة PDF.
- `ADMIN_SECRET` — `/admin/orders/{code}/approve` و `admin-pitch.html`.

## بعد التحديث

```bash
git push origin main
```

Coolify → **Redeploy** (Rebuild `web` + `api` + `worker`).
