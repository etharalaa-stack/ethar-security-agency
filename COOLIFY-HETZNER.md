# نشر ETHAR LABS على Hetzner + Coolify (128.140.121.115)

السيرفر: **Hetzner** · لوحة Coolify: `http://128.140.121.115:8000` · المستودع: `etharalaa-stack/ethar-security-agency`

---

## A) رفع الكود إلى GitHub (مرة قبل Coolify)

```bash
cd "/mnt/velocity/Multi-Agent Swarm/backend-engine"
./scripts/sync-frontend.sh
git add .
git status
git commit -m "Coolify fullstack deploy and production runbooks"
git push -u origin main
```

(استخدم **GitHub PAT** ككلمة مرور عند `git push`.)

---

## B) Coolify — إنشاء المشروع (كما في الصورة)

1. افتح **http://128.140.121.115:8000** → Project **production**.
2. **+ New** → **Resource** → **Public Repository** (أو GitHub App إن كانت مربوطة).
3. Repository: `https://github.com/etharalaa-stack/ethar-security-agency`
4. Branch: `main`
5. **Build Pack:** `Docker Compose`
6. **Docker Compose location:** `docker-compose.coolify.yml`
7. **Base Directory:** `/` (جذر الم repo)

---

## C) متغيرات البيئة (Environment)

1. في Coolify → Resource → **Environment Variables**.
2. انسخ محتوى `.env.coolify.example` وعدّل:
   - `YOUR_PUBLIC_URL` → الرابط العام الذي يعطيك إياه Coolify للخدمة **web** (مثلاً `https://agency.yourdomain.com` أو FQDN من Coolify).
   - `ADMIN_SECRET` → `openssl rand -hex 32`
3. **مهم:** Coolify يحقن المتغيرات لكل الحاويات (`api`, `worker`, `web` لا تحتاج `.env` في Git).

**بدون دومين (اختبار IP):** في Coolify → Service **web** → **Generate Domain** أو Port mapping، ثم:

```env
PUBLIC_API_BASE_URL=http://128.140.121.115:PORT
FRONTEND_URL=http://128.140.121.115:PORT
CORS_ORIGINS=*
```

---

## D) ربط الدومين / المنفذ

1. Resource → Service **`web`** (nginx — الواجهة + `/api` proxy).
2. **Domains** → أضف دومينك أو **Generate** FQDN.
3. فعّل **HTTPS** (Let's Encrypt) إن وُجد دومين.
4. **لا** تربط الدومين بخدمة `api` مباشرة — العميل يدخل من `web` فقط.

---

## E) Deploy

1. **Deploy** (أو Redeploy).
2. انتظر حتى **web** و **api** **Healthy**.
3. من جهازك:

```bash
cd "/mnt/velocity/Multi-Agent Swarm/backend-engine"
chmod +x scripts/smoke-production.sh
./scripts/smoke-production.sh "https://YOUR_PUBLIC_URL"
```

---

## F) اختبار أعمال (نفس المحلي)

| خطوة | URL |
|------|-----|
| الرئيسية | `https://YOUR_PUBLIC_URL/index.html` |
| Pitch admin | `https://YOUR_PUBLIC_URL/admin-pitch.html` |
| API docs | `https://YOUR_PUBLIC_URL/docs` |
| طلب تجريبي | Card Ref **`STRIPE-TEST-001`** (حتى تفعّل USDT حقيقي) |
| موافقة PDF | `POST .../admin/orders/ORD-XXXX/approve?secret=ADMIN_SECRET` |

---

## G) ترتيب الإنتاج (أرباح حقيقية)

1. `USDT_*` + `BSCSCAN_API_KEY` في Coolify env.
2. `TELEGRAM_*` للتنبيهات و HITL.
3. `STAGE_DELAY_SECONDS=3600` للإيقاع الواقعي.
4. أزل الاعتماد على `STRIPE-TEST-*` للعملاء (أبقِ البادئة للاختبار الداخلي فقط).

---

## H) استكشاف الأخطاء

| عرض | حل |
|-----|-----|
| 502 على `/api` | `api` غير healthy — Logs في Coolify |
| الواجهة بدون API | تأكد الدومين على **web** وليس api |
| Pitch links بـ localhost | عدّل `FRONTEND_URL` في Coolify → Redeploy |
| Build fail | تأكد `frontend-cloudflare/` موجود في Git (`sync-frontend.sh`) |

---

## I) أوامر على السيرفر (SSH اختياري)

```bash
ssh root@128.140.121.115
docker ps
docker logs -f <api-container-id>
```

Coolify يدير Compose؛ يفضّل التعديل من لوحة Coolify لا يدوياً على `/data/coolify/...` إلا للطوارئ.
