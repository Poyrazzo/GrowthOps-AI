# Go-Live Runbook
## Growth Automation & AI Ops System

This document is the complete, ordered checklist to take the system from the current codebase to a fully operating outreach machine — including every external account, API key, DNS record, and seed-data step. Everything here is grounded in what the code actually reads (env vars, model fields, URLs), so it can be followed literally.

> **Critical-path summary:** OpenAI key → `.env` → change `SECRET_KEY` (BEFORE saving any mailbox passwords!) → mailboxes + SPF/DKIM/DMARC → `docker compose up` + migrate + superuser → seed EmailAccounts / LeadMagnets / Campaign / LeadSources → run the two E2E tests + one manual scrape → activate the campaign.

---

## Phase A — Accounts & keys to obtain

### 1. OpenAI (required — the brain)
- Create an account at platform.openai.com, add a payment method, and create an API key.
- The entire AI layer (`backend/ai_engine/llm.py`) uses `gpt-4o-mini`, which is cheap (~$0.15 / 1M input tokens). Set a monthly usage limit ($10–20 is plenty to start).

### 2. Langfuse (optional — AI observability)
- Free account at cloud.langfuse.com → create a project → copy the public + secret keys.
- If you skip this, the system runs fine: `get_langfuse_handler()` returns `None` and tracing is simply off.

### 3. Outreach domain + mailboxes (required — the most important non-code step)
- **Do not send cold email from your main domain.** Buy a lookalike domain (e.g., `getgrowthops.com` if your real site is `growthops.com`) — cold outreach burns domain reputation.
- Create 1–3 mailboxes on it. Easiest paths: Google Workspace (~$6/user/mo) or Zoho Mail. You need real SMTP + IMAP credentials per mailbox.
  - Google Workspace: enable 2FA, then create an **App Password** (regular passwords will not work over SMTP/IMAP). SMTP `smtp.gmail.com:587` (tls), IMAP `imap.gmail.com:993` (ssl).
- **DNS records on that domain (SPF / DKIM / DMARC — SRS 3.11).** These live at your DNS provider, not in our code:
  - SPF: `v=spf1 include:_spf.google.com ~all` (provider-specific include)
  - DKIM: generate in the mail provider's admin console, paste the TXT record into DNS
  - DMARC: `_dmarc` TXT → `v=DMARC1; p=quarantine; rua=mailto:you@yourdomain`
  - Verify all three with a free tool (MXToolbox, learndmarc.com) **before sending anything**.
- **Warm up:** new mailboxes should send ~10–20/day for 2–3 weeks before raising volume. Set `daily_limit=15` initially (the `EmailAccount.daily_limit` field is enforced per-account per-day).

### 4. Slack or Discord webhook (optional — hot-lead alerts)
- Slack: create an app → Incoming Webhooks → copy the URL.
- Discord: channel settings → Integrations → Webhooks → copy the URL.

### 5. AdsPower (optional — only for anti-detect dynamic scraping)
- Install the AdsPower desktop app on the **host machine**, create browser profiles, enable the Local API (default `http://localhost:50325`).
- The code reaches it via `host.docker.internal:50325` (`backend/scraper/adspower.py`), already wired through `extra_hosts` in docker-compose. Plain Playwright scraping works without AdsPower.

### 6. Proxies (optional)
- A residential/datacenter proxy provider (e.g., Webshare, IPRoyal) if you will scrape at volume. Proxy URLs are passed per scrape task; not needed for low-volume starts.

---

## Phase B — Configure the project

### 7. Create a `.env` file in the repo root
Place it next to `docker-compose.yml` — Compose reads it automatically for the `${...}` substitutions:

```env
OPENAI_API_KEY=sk-...
LANGFUSE_SECRET_KEY=sk-lf-...        # or leave empty
LANGFUSE_PUBLIC_KEY=pk-lf-...        # or leave empty
LANGFUSE_HOST=https://cloud.langfuse.com
```

Optional tuning (read by `backend/core/settings.py`; all have sane defaults — only set to override):

```env
LEAD_SCORE_THRESHOLD=70          # min score for auto-outreach
REPLY_CONFIDENCE_THRESHOLD=0.85  # below this, replies go to human review
SCRAPE_REFRESH_HOURS=24          # per-source re-scrape cooldown
```

Add `.env` to `.gitignore` if it is not already there.

### 8. Change the Django `SECRET_KEY` — NOW, before storing any mailbox passwords
The Fernet encryption key for mailbox passwords derives from `SECRET_KEY` (`backend/core/encryption.py`). **Changing it later makes already-stored passwords undecryptable.** Edit `backend/core/settings.py` (line ~23); ideally read it from the `.env` as well:

```python
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '<a long random string>')
```

(If you do this, also add `DJANGO_SECRET_KEY=...` to `.env` and pass it through in `docker-compose.yml` for the `django`, `celery_worker`, `celery_beat`, and `playwright_worker` services.)

### 9. Slack alert wiring (n8n)
Nothing to change in our code — the webhook URL `http://n8n:5678/webhook/growthops-events` is already hardcoded in `backend/crm/utils.py`. The Slack URL itself is configured inside n8n (Phase C, step 12).

---

## Phase C — Bring the stack up

### 10. Build and start everything
```bash
docker compose up -d --build
```
After any later edit to `.env` or settings: `docker compose up -d` plus
```bash
docker compose restart celery_worker celery_beat playwright_worker
```
**Remember: Celery workers do NOT hot-reload code** even with the volume mount (see the Operational Note in `experience.md`).

### 11. Apply migrations and create your admin user
```bash
docker compose exec django python manage.py migrate
docker compose exec django python manage.py createsuperuser
```

### 12. Set up n8n (one-time, in the browser)
1. Open `http://localhost:5678` → create the owner account on first launch.
2. Import `n8n_workflows/Slack_Notification_Template.json` (Workflows → Import from File).
3. Open the **Send Alert** node and replace `YOUR_SLACK_OR_DISCORD_WEBHOOK_URL_HERE` with your real webhook URL.
4. **Activate the workflow** (toggle, top-right). This matters: the production `/webhook/growthops-events` path that Django posts to only listens while the workflow is *active* (test mode uses a different `/webhook-test/` path).

---

## Phase D — Seed your operating data
Django admin: `http://localhost:18000/admin/` (or the dashboard at `http://localhost:3000`).

### 13. Email Accounts (one per mailbox)
| Field | Value |
|---|---|
| `email`, `username` | the mailbox address |
| `password_encrypted` | paste the **plain** app password — it auto-encrypts on save |
| `smtp_host` / `smtp_port` | provider values; port **587 → `smtp_encryption='tls'`**, port **465 → `'ssl'`** |
| `imap_host` / `imap_port` | usually 993, `imap_use_ssl` ✓ |
| `daily_limit` | **15** while warming up |
| `is_active` | ✓ |

### 14. Lead Magnets
Name, description, URL, `target_persona`. The scoring AI picks from this catalog per lead — **write the descriptions like you are telling a salesperson when to use each one.**

### 15. Campaign
Via admin or the dashboard (`/campaigns`): sector, country, persona, value proposition (this text goes directly into every AI prompt — write it well), channel (`email` or `linkedin`), start/end dates.
**Leave `status='draft'` until Phase E is verified.**

### 16. Lead Sources
URL, `source_type` (`static` / `dynamic` / `directory` — *directory matters*: it changes company attribution so leads aren't attributed to the directory site), sector, `priority_score`, and **set the `campaign` FK** — sources without a campaign are never auto-scraped. (`linkedin`-type sources are never auto-scraped at all, by compliance design.)

---

## Phase E — Verify before going live

### 17. Run the built-in E2E suites (no external accounts needed — uses GreenMail)
```bash
docker compose exec django python manage.py test_e2e_email
docker compose exec django python manage.py test_e2e_linkedin
```
Both must fully pass (outbound dispatch, GreenMail interception, inbound IMAP reply matching, stop-condition transition; LinkedIn task completion → AuditLog + Activity + lead state).

### 18. Test one real scrape manually (before trusting the scheduler)
```bash
curl -X POST http://localhost:18000/api/crm/leadsources/<source-uuid>/scrape/
```
Watch `docker compose logs -f celery_worker` and check Leads in admin/dashboard. Verify companies look right and scores/drafts appear — this is also your first live OpenAI call, so confirm there are no auth errors in the worker log.

### 19. Test the human loop
With `requires_human_review=True` (the default on every lead), drafts land in the Approval Queue at `http://localhost:3000/approvals` — you should see the full email body and lead context. Approve one and confirm it sends (next dispatch run is within 10 minutes; the message flips to `sent` and arrives **threaded** in a test inbox you control).

### 20. Test the reply loop
Reply to that test email from the recipient inbox. Within ~5 minutes the IMAP poller should create a `Reply`, classify it, flip the lead to `replied`, and — if positive — ping your Slack via n8n.

---

## Phase F — Go live & operate

### 21. Flip the campaign to `status='active'`
From here the machine runs itself:
- Beat scrapes due sources every **6h** (per-source 24h cooldown)
- Enriches → scores → drafts → queues approvals
- Dispatches every **10 min** within daily limits
- Polls inboxes every **5 min**
- Follow-ups after **3 days** of silence (max 3 emails per sequence, threaded as `Re:`)
- Auto-suppresses bounces/unsubscribes globally

Pausing the campaign genuinely stops scraping/drafting/sending. LinkedIn campaigns: work the task queue at `/tasks` daily — completing a connect task auto-generates the DM task.

### 22. Daily operator routine
- Clear the Approval Queue (drafts + low-confidence reply reviews)
- Execute LinkedIn manual tasks
- Skim AuditLog / Activities in admin for anomalies
- Watch bounce-driven suppressions: **rising bounces = deliverability problem → lower `daily_limit` immediately**

---

## ⚠️ Before exposing anything beyond your laptop

The API currently has **no authentication**, `DEBUG=True`, and `ALLOWED_HOSTS` is localhost-only. That is fine for a single-machine setup (ports bind to localhost), but **if you ever deploy or port-forward**:
1. Add DRF token/session authentication + permission classes
2. Set `DEBUG=False` and proper `ALLOWED_HOSTS`
3. Move `SECRET_KEY` / DB credentials fully to env vars
4. Put frontend + backend behind HTTPS (reverse proxy)

Also still open from the audit (fine to defer; does not affect operation): real analytics aggregation endpoints — the dashboard "Outreach Velocity" chart is mock data.
