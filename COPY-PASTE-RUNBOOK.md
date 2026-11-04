# ETHAR LABS UK LTD — Copy/Paste Runbook (كل الأوامر جاهزة)

استبدل فقط القيم بين `<>` بقيمك الحقيقية.

---

## 1) أول مرة — تجهيز الجهاز (مرة واحدة)

```bash
cd "/mnt/velocity/Multi-Agent Swarm/backend-engine"

sudo apt update
sudo apt install -y python3-venv python3-pip git curl

chmod +x scripts/*.sh start-dev.sh

./scripts/setup.sh
```

---

## 2) تشغيل محلي كامل (كل يوم)

```bash
cd "/mnt/velocity/Multi-Agent Swarm/backend-engine"
API_PORT=9815 ./start-dev.sh
```

افتح:

- http://127.0.0.1:8788/index.html  
- http://127.0.0.1:9815/docs  

**إيقاف:** `Ctrl+C` في نفس التيرمنل.

### إذا ظهر `Address already in use` أو `port 9815 is already in use`

**أ) المنصة شغّالة أصلاً — استخدمها بدون تشغيل ثانية:**

- http://127.0.0.1:8788/index.html  
- http://127.0.0.1:9815/docs  

**ب) إيقاف النسخة القديمة ثم إعادة التشغيل:**

```bash
fuser -k 9815/tcp 8788/tcp 2>/dev/null
pkill -f 'backend-engine/.venv.*uvicorn app.main' 2>/dev/null
pkill -f 'backend-engine.*run-worker' 2>/dev/null
sleep 1
cd "/mnt/velocity/Multi-Agent Swarm/backend-engine"
API_PORT=9815 ./start-dev.sh
```

**ج) منافذ بديلة (بدون قتل العمليات الأخرى):**

```bash
cd "/mnt/velocity/Multi-Agent Swarm/backend-engine"
API_PORT=9816 FRONT_PORT=8789 ./start-dev.sh
```

---

## 3) بعد تعديل الواجهة — مزامنة + Git

```bash
cd "/mnt/velocity/Multi-Agent Swarm/backend-engine"
./scripts/sync-frontend.sh
git add .
git status
git commit -m "Update platform"
git push -u origin main
```

> عند `git push`: Username = `etharalaa-stack` — Password = **GitHub PAT** (ليس كلمة مرور GitHub).

---

## 4) إنشاء GitHub PAT (مرة واحدة)

1. افتح: https://github.com/settings/tokens  
2. **Generate new token (classic)** → Scope: **repo**  
3. انسخ التوken.

```bash
git config --global credential.helper store
cd "/mnt/velocity/Multi-Agent Swarm/backend-engine"
git push -u origin main
```

---

## 5) SSH بدل PAT (اختياري)

```bash
ssh-keygen -t ed25519 -C "your-email@example.com" -f ~/.ssh/id_ed25519_github -N ""
cat ~/.ssh/id_ed25519_github.pub
```

أضف المفتاح في: https://github.com/settings/keys

```bash
cd "/mnt/velocity/Multi-Agent Swarm/backend-engine"
git remote set-url origin git@github.com:etharalaa-stack/ethar-security-agency.git
git push -u origin main
```

---

## 6) ملف `.env` للتطوير (Copy/Paste)

```bash
cd "/mnt/velocity/Multi-Agent Swarm/backend-engine"
cp -n .env.example .env
nano .env
```

**محتوى `.env` محلي جاهز (عدّل المحفظة لاحقاً):**

```env
DEBUG=true
PORT=9815
PUBLIC_API_BASE_URL=http://127.0.0.1:9815
FRONTEND_URL=http://127.0.0.1:8788
CORS_ORIGINS=*

DATABASE_URL=sqlite+aiosqlite:///./data/agency.db
DATABASE_URL_SYNC=sqlite:///./data/agency.db
STAGE_DELAY_SECONDS=15

USDT_BEP20_WALLET=<YOUR_BEP20_WALLET>
USDT_TRC20_WALLET=<YOUR_TRC20_WALLET>
BSCSCAN_API_KEY=<YOUR_BSCSCAN_KEY_OR_LEAVE_EMPTY_FOR_DEV>

STRIPE_WEBHOOK_SECRET=
STRIPE_TEST_REFERENCE_PREFIX=STRIPE-TEST-

OPENAI_API_KEY=<OPTIONAL_LLM_KEY>
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
LLM_PROVIDER=openai
LLM_TIMEOUT_SECONDS=90
OPENROUTER_HTTP_REFERER=
OPENROUTER_APP_TITLE="ETHAR LABS UK LTD"

TELEGRAM_BOT_TOKEN=<BOT_TOKEN>
TELEGRAM_CHAT_ID=<CHAT_ID>
ADMIN_SECRET=<RANDOM_SECRET>
```

**توليد ADMIN_SECRET:**

```bash
openssl rand -hex 32
```

---

## 7) ملف `.env` للإنتاج على السيرفر (Copy/Paste)

```bash
cd "/mnt/velocity/Multi-Agent Swarm/backend-engine"
cp .env.production.example .env
nano .env
./scripts/validate-env.sh
```

---

## 8) Telegram Bot (Copy/Paste)

1. Telegram → `@BotFather` → `/newbot` → انسخ **Token**  
2. `@userinfobot` → انسخ **Chat ID**  
3. ضعهما في `.env`:

```env
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=123456789
```

---

## 9) اختبار طلب كامل محلياً (Copy/Paste)

**أ) من المتصفح:**  
http://127.0.0.1:8788/index.html → اختر Parts → Card Ref → `STRIPE-TEST-001`

**ب) أو API:** (يجب أن يكون `./start-dev.sh` **شغّالاً** في طرفية أخرى — بعد `Ctrl+C` لن يرد `curl` شيء)

```bash
curl -sS -X POST "http://127.0.0.1:9815/api/v1/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "client_email": "client@example.com",
    "organization": "Test Corp",
    "selected_parts": ["part_1", "part_3"],
    "target_asset": "https://example.com",
    "payment_plan": "full",
    "payment_method": "card_reference",
    "card_reference": "STRIPE-TEST-001",
    "authorized_scope": true
  }'
```

انسخ `order_id` من الرد (مثل `ORD-1234`).

**تتبع:**

http://127.0.0.1:8788/track.html?order=ORD-1234

**موافقة Admin (استبدل SECRET و ORD):**

```bash
curl -X POST "http://127.0.0.1:9815/api/v1/admin/orders/ORD-1234/approve?secret=<ADMIN_SECRET>"
```

**تحميل PDF:**

http://127.0.0.1:9815/api/v1/orders/ORD-1234/report

---

## 10) Quick Scan (Copy/Paste)

```bash
curl -s -X POST "http://127.0.0.1:9815/api/v1/public/quick-scan" \
  -H "Content-Type: application/json" \
  -d '{"target":"example.com","organization":"Demo Corp"}' | python3 -m json.tool
```

**رابط pitch للعميل (محلي):**

```
http://127.0.0.1:8788/index.html?target=example.com&org=Demo%20Corp
```

---

## 11) Admin Pitch CRM (Copy/Paste)

```bash
curl -s -X POST "http://127.0.0.1:9815/api/v1/admin/pitch/generate?secret=<ADMIN_SECRET>" \
  -H "Content-Type: application/json" \
  -d '{
    "prospects": [
      {"domain": "client.com", "organization": "Client Inc"},
      {"domain": "acme.io", "organization": "Acme Ltd"}
    ]
  }' | python3 -m json.tool
```

أو من المتصفح: http://127.0.0.1:8788/admin-pitch.html

---

## 12) نشر Docker Full Stack على VPS/Coolify (Copy/Paste)

```bash
cd "/mnt/velocity/Multi-Agent Swarm/backend-engine"
./scripts/sync-frontend.sh
cp .env.production.example .env
nano .env
./scripts/validate-env.sh

docker compose -f docker-compose.fullstack.yml up -d --build
docker compose -f docker-compose.fullstack.yml ps
curl -s http://127.0.0.1:8080/health
```

- الموقع: http://`<SERVER_IP>`:8080/index.html  
- API عبر نفس الدومين: `/api/v1/...`

---

## 13) Cloudflare Pages (Frontend فقط) — Copy/Paste

**في السيرفر/جهازك — ملف production للواجهة:**

```bash
cd "/mnt/velocity/Multi-Agent Swarm/backend-engine/frontend-cloudflare/assets"
cp config.production.example.js config.production.js
nano config.production.js
```

```javascript
window.AGENCY_API_BASE = "https://<YOUR_API_DOMAIN>/api/v1";
```

**Cloudflare Dashboard:**

- Pages → Create → Connect GitHub `ethar-security-agency`  
- Root directory: `frontend-cloudflare`  
- Build: (none)  
- Deploy  

**على API `.env`:**

```env
CORS_ORIGINS=https://<YOUR_PAGES>.pages.dev,https://<YOUR_DOMAIN>
FRONTEND_URL=https://<YOUR_DOMAIN>
PUBLIC_API_BASE_URL=https://<YOUR_API_DOMAIN>
```

---

## 14) Railway (API + Worker) — Copy/Paste

1. railway.app → New Project → Deploy from GitHub → `backend-engine`  
2. Variables: انسخ كل `.env.production.example`  
3. Start command (إن طُلب):

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

4. Service ثاني للـ worker:

```bash
python -m app.worker
```

---

## 15) Coolify + Hetzner (128.140.121.115) — Copy/Paste

**دليل كامل:** [`COOLIFY-HETZNER.md`](COOLIFY-HETZNER.md)

```bash
cd "/mnt/velocity/Multi-Agent Swarm/backend-engine"
./scripts/coolify-one-shot.sh
git push -u origin main
```

في Coolify (`http://128.140.121.115:8000`):

1. **production** → New → Public Repository → `etharalaa-stack/ethar-security-agency`  
2. **Docker Compose** → `docker-compose.coolify.yml`  
3. **Environment** → انسخ `.env.coolify.example` + `ADMIN_SECRET=$(openssl rand -hex 32)`  
4. Domain على service **`web`** فقط → Deploy  
5. `./scripts/smoke-production.sh "https://YOUR_PUBLIC_URL"`

---

## 16) OpenRouter / DeepSeek (LLM) — Copy/Paste

```env
OPENAI_API_KEY=<OPENROUTER_KEY>
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=deepseek/deepseek-chat
LLM_PROVIDER=openrouter
OPENROUTER_HTTP_REFERER=https://yourdomain.com
OPENROUTER_APP_TITLE="ETHAR LABS UK LTD"
```

---

## 17) إيقاف كل الخدمات (Copy/Paste)

```bash
cd "/mnt/velocity/Multi-Agent Swarm/backend-engine"
./scripts/stop-dev.sh
docker compose -f docker-compose.fullstack.yml down 2>/dev/null || true
```

---

## 18) checklist أرباح حقيقية

- [ ] `.env` إنتاج + `./scripts/validate-env.sh`  
- [ ] محافظ USDT + BSCScan  
- [ ] Telegram يعمل  
- [ ] نشر public (8080 أو CF+Railway)  
- [ ] `config.production.js` على Cloudflare  
- [ ] Pitches من admin-pitch  
- [ ] لا `STRIPE-TEST` في الإنتاج — USDT حقيقي فقط  
