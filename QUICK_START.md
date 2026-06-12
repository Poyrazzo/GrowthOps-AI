# GrowthOps AI - Quick Start (UI Ready)

Get the system running in 5 minutes. Everything else is done from the UI.

---

## Prerequisites

- Docker & Docker Compose installed
- `.env` file with API keys (already created in project root)

---

## 1️⃣ Verify `.env` File

Open `.env` in project root and make sure it has:

```env
OPENAI_API_KEY=sk-...your-key...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
OUTREACH_EMAIL=your-email@gmail.com
OUTREACH_APP_PASSWORD=your-16-char-password
ADSPOWER_PROFILE_ID=your-profile-id
DJANGO_SECRET_KEY=...
```

If any are missing, add them now.

---

## 2️⃣ Start the System

```bash
cd /path/to/GrowthOps\ AI

# Start all services
docker compose up -d --build

# Watch the logs (Ctrl+C to stop watching)
docker compose logs -f
```

**Wait for this line to appear:**
```
celery@... ready.
```

This means everything is started (~30-60 seconds).

---

## 3️⃣ Open the System

Once running, open in your browser:

| What | URL | Login |
|------|-----|-------|
| Dashboard | http://localhost:3000 | (no login) |
| Admin Panel | http://localhost:18000/admin | admin / P19figureit.out |

---

## ✅ Done!

You're ready to use the UI:
- Create campaigns at `/campaigns`
- View leads at `/`
- Approve messages at `/approvals`
- View campaign status by clicking a campaign card

---

## Stop the System

```bash
docker compose down
```

---

## Logs & Debugging

```bash
# View all logs
docker compose logs -f

# View one service
docker compose logs -f django
docker compose logs -f celery_worker

# Restart a service
docker compose restart django
```

---

## If Something's Wrong

1. Check all containers are running:
   ```bash
   docker compose ps
   ```

2. Check logs for errors:
   ```bash
   docker compose logs django
   ```

3. Restart everything:
   ```bash
   docker compose down
   docker compose up -d --build
   ```

---

**That's it! Use the UI for everything else.**
