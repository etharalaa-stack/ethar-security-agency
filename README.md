# ETHAR LABS UK LTD — Security Agency Backend (v2.1)

FastAPI API, async worker, modular audits, quick-scan, Telegram HITL.

Static frontend lives in sibling folder: `../frontend-cloudflare/` (deploy to Cloudflare Pages).

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
./start-dev.sh
```

## Docker / Coolify / Railway

```bash
docker compose up --build
```

Use `coolify.compose.yaml` on Coolify. Set `PORT`, secrets, and persistent volumes for `data/` and `generated_reports/`.
# ethar-security-agency
