# إمكانيات المدفوع — ETHAR LABS UK LTD

## طرق الدفع

| الطريقة | للعميل | التحقق على السيرفر |
|---------|--------|---------------------|
| **USDT BEP20** | يرسل USDT لمحفظتك + TxHash | BscScan receipt + عقد USDT + المبلغ |
| **USDT TRC20** | يرسل USDT + TxHash | TronGrid events + المحفظة + المبلغ |
| **Card / Invoice Ref** | `INV-*` أو `CARD-*` | تسجيل + مطابقة يدوية |
| **STRIPE-TEST-*** | تجريبي فقط | يعمل إذا `ALLOW_TEST_PAYMENTS=true` أو `DEBUG=true` |
| **Stripe Checkout** | (اختياري) | Webhook `checkout.session.completed` + metadata `order_code` |

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

## Stripe (اختياري)

1. أنشئ Checkout Session مع `metadata.order_code=ORD-XXXX`.
2. Webhook URL: `https://YOUR-DOMAIN/api/v1/webhooks/stripe`
3. عند `checkout.session.completed` يُفعَّل الطلب تلقائياً.

## Telegram + PDF

- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` — تنبيه دفع + رابط موافقة PDF.
- `ADMIN_SECRET` — `/admin/orders/{code}/approve` و `admin-pitch.html`.

## بعد التحديث

```bash
git push origin main
```

Coolify → **Redeploy** (Rebuild `web` + `api` + `worker`).
