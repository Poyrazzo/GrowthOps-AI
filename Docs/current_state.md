# Current State

This document serves as the single source of truth for the current state of the Growth Automation & AI Ops System. 

## Architecture Status
- **Docker Compose:** Fully initialized with `postgres` (15), `redis` (7-alpine), `django`, `celery_worker`, `celery_beat`, `playwright_worker`, and `frontend` services.
- **Backend:** Django and Django REST Framework initialized in the `backend/` directory. 
  - CORS is configured to allow Next.js (`http://localhost:3000`) to fetch API data securely.
  - Celery is configured with Redis as the broker and PostgreSQL (`django-celery-results`) as the result backend.
- **CRM App:** `crm` app initialized. Core models, secondary models, and utility models (`SuppressionList`, `EmailAccount`, `AuditLog`, etc.) are fully mapped to Postgres.
- **API Endpoints:** DRF serializers, viewsets, and a DefaultRouter are implemented. All 12 CRM models are fully exposed via REST APIs.
- **Scraping Engine (Phase 3):** 
  - Fully functional static (`requests`) and dynamic (`Playwright`) scrapers with proxy support, AdsPower isolation, and Pandas data normalization.
  - Celery orchestration connects the entire pipeline with exponential backoff retry mechanisms.
- **AI Enrichment & Classification (Phase 4):** 
  - Fully autonomous Celery pipeline: Scrape -> Clean -> Save Leads -> Enrich Company -> Score Leads -> Draft Emails. 
  - Guarded against infinite loops and uniquely constrained to save OpenAI tokens via Langfuse.
- **Outreach Engine (Phase 5):**
  - **Security:** Integrated `cryptography` (Fernet) to securely encrypt `EmailAccount` passwords via Django's `SECRET_KEY`.
  - **SMTP Sender:** Implemented `backend/outreach/smtp.py` with suppression list checking and Thread ID tracking (`Message-ID`).
  - **IMAP Reader:** Implemented `backend/outreach/imap.py` with scheduled Celery Beat polling to match incoming replies using metadata headers.
  - **AI Reply Classification:** Implemented `backend/ai_engine/reply_classifier.py`. Incoming replies are instantly chained to a `gpt-4o-mini` classification pipeline.
  - **Autonomous Suppression Loop:** If the AI classifies a reply as `unsubscribe` or `bounce`, the system autonomously blocks the lead by inserting them into the `SuppressionList` and disqualifying them.
  - **Sequence Manager:** A background task `dispatch_emails_task` runs every 10 minutes to dispatch pending drafts. A second task `process_followups_task` runs every hour, analyzing all leads `in_sequence` and invoking the AI to write follow-ups if no reply has been received in 3 days.
- **Frontend App (Phase 6):**
  - **Framework:** Next.js (App Router), `shadcn/ui`, Tailwind v4, and `framer-motion`.
  - **Aesthetics:** Implemented a deeply professional, highly customized "Deep Space Glassmorphic" dark theme. 
  - **Layout (Step 6.1):** Built the core Dashboard layout. 
    - `Sidebar.tsx`: A fluid, framer-motion powered collapsible navigation bar with glowing active states and hover micro-interactions.
    - `Header.tsx`: A frosted glass (`backdrop-blur-md`) top navigation.
  - **Campaigns View (Step 6.2):** 
    - `lib/api.ts`: Centralized Data-fetching service using native `fetch` mapped to the Django backend.
    - `(dashboard)/campaigns/page.tsx`: A dynamic `react-query` powered grid of Campaign Cards. Shows campaign status badges, Target Persona details, and outreach channel. Uses Framer Motion's `staggerChildren` for animated entrances.
    - `components/ui/campaign-modal.tsx`: A sleek, animated glass sliding overlay for creating new Campaigns. Uses `useMutation` to automatically invalidate and refetch the campaign list upon successful creation.
  - **Leads View (Step 6.3):** 
    - `(dashboard)/leads/page.tsx`: An animated Data Table listing all AI-enriched leads. Features search filtering, dynamic glass-row hover effects, and distinct, color-coded badges for Lead Status and Score thresholds. 
    - `components/ui/lead-slideover.tsx`: Instead of navigating to a separate page, clicking a lead opens a frosted-glass sliding panel (`x: "100%" -> 0`) from the right side of the screen. This panel cleanly presents the AI's intelligence report (`score_reason` and `recommended_message_angle`).
  - **Approval Queue (Step 6.4):**
    - `(dashboard)/approvals/page.tsx`: A dedicated audit interface displaying all `pending` items from the `ApprovalQueue` API. Uses Framer Motion's staggered grid layout. Operators can click "Approve" (Emerald glow) or "Reject" (Destructive glow) to dispatch or block drafts. Actions are tied to TanStack's `useMutation` for zero-reload optimistic UI updates.
  - **LinkedIn Manual Tasks (Step 6.5):**
    - `components/layout/Sidebar.tsx`: Added `/tasks` route.
    - `(dashboard)/tasks/page.tsx`: A grid of pending manual LinkedIn social-selling tasks. The UI extracts and highlights the task instructions. It uses TanStack Query to immediately dismiss completed/failed cards from the queue with smooth spring physics.
  - **Analytics and Reporting (Step 6.6):**
    - `(dashboard)/page.tsx`: The primary dashboard index now features a premium, edge-to-edge `recharts` AreaChart depicting "Outreach Velocity". The chart utilizes SVG `<defs>` to inject deep electric purple, cyan, and emerald gradients into the chart fill, maintaining the dark "Deep Space" aesthetic. It integrates `framer-motion` for smooth rendering. (Note: Currently powered by mock time-series data until backend aggregation endpoints are developed).
  - **Phase 6 Audit Fixes:**
    - `backend/crm/models.py`: Added `'needs_review'` to `Message.STATUS_CHOICES`.
    - `backend/crm/tasks.py`: Updated `generate_draft_task` to respect the `lead.requires_human_review` boolean. When true, messages default to `'needs_review'` and automatically spawn `ApprovalQueue` records.
    - `backend/crm/views.py`: Overrode `perform_update` in `ApprovalQueueViewSet`. Approving a task now actively patches the underlying `Message` status to `'pending'` for dispatch, closing the critical logic gap.
    - `(dashboard)/sources/page.tsx`: Built the previously missing Lead Source Manager UI featuring priority scoring, access rules, and `framer-motion` cards.

- **Current Completion:** Phase 1, Phase 2, Phase 3, Phase 4, Phase 5, and Phase 6 are entirely complete and fully audited.

## Phase 7: Integration, Workflows, and Testing
  - **n8n Container & Webhooks (Step 7.1):**
    - `docker-compose.yml`: Added `n8nio/n8n` container mapping to port `5678` with a dedicated persistent volume (`n8n_data`).
    - `backend/crm/utils.py`: Built `send_notification_webhook` to blast POST requests across the internal Docker network to n8n (`http://n8n:5678/webhook/growthops-events`).
    - `backend/crm/tasks.py`: Updated `process_reply_task` to instantly trigger the n8n webhook when the AI detects a `positive` sentiment reply.
    - `n8n_workflows/Slack_Notification_Template.json`: Constructed a visual node template featuring a Webhook trigger, an Event Router, and an HTTP Request node dynamically mapping the JSON payload to Slack/Discord markdown formatting.
  - **E2E Email Testing (Step 7.2):**
    - `docker-compose.yml`: Added `greenmail/standalone` container, providing a mock SMTP (port 3025), IMAP (port 3143), and REST API (port 8080) environment.
    - `backend/crm/management/commands/test_e2e_email.py`: Built an automated test harness that provisions a mock `EmailAccount`, seeds a `Lead`, drafts a message, mathematically asserts the database state transitions to `sent` via Celery logic, and queries the `greenmail` REST API to physically verify the mock server received the payload.
  - **LinkedIn Manual Workflow Validation (Step 7.3):**
    - `backend/crm/views.py`: Overrode `perform_update` in `LinkedInTaskViewSet`. When the frontend patches a task to `completed`, the backend automatically generates an `AuditLog` entry (proving Human-in-the-Loop action) and transitions the `Lead` status from `uncontacted` to `in_sequence`.
    - `backend/crm/management/commands/test_e2e_linkedin.py`: Built a Django test harness using `APIClient` to fully simulate an operator clicking "Mark Complete" on the Next.js dashboard, mathematically asserting the CRM state and Audit Log updates.
  - **Compliance & Security Auditing (Step 7.4):**
    - `backend/outreach/sequence.py`: Patched a massive vulnerability where automated follow-up drafts bypassed human gates. Follow-ups now respect `lead.requires_human_review`, spawning `ApprovalQueue` tasks instead of bypassing into `pending` state.
  - **Phase 7 Final Audit & Bug Fixes (Step 7.5):**
    - `backend/crm/tasks.py`: Injected missing `send_notification_webhook` logic. Now, positive incoming replies correctly and safely push real-time webhooks to the external n8n cluster.
    - `backend/crm/management/commands/test_e2e_email.py` & `test_e2e_linkedin.py`: Fixed the `Campaign` database model seeding schemas, removing the nonexistent `daily_limit` field and adding all necessary mandatory fields to prevent Postgres integrity crashes.
    - `backend/outreach/smtp.py`: Added dynamic fallback `use_tls=(self.account.smtp_port not in [3025, 1025, 2525])` so the `EmailBackend` cleanly pushes payloads to local mock servers without throwing `STARTTLS` exceptions.

## Post-Phase 7 Independent Audit (2026-06-11)
A full-system audit was performed against the SRS and original PDF goals. Architecture and module coverage largely match the intended design, but the system is **not yet functional end-to-end** due to confirmed blocking bugs (see the matching entry in `experience.md` for the full list). Highest-priority blockers before the system can be considered working:
1. `scraper/cleaner.py` dedup collapses every scrape to a single lead + converts null emails to the string `'none'` (verified).
2. Nothing triggers scraping (no API/beat caller of the scrape tasks; `LeadSource` unused).
3. Frontend `api.ts` points at port 8000; Docker exposes Django on 18000.
4. Approval Queue UI does not display the email draft being approved.
5. Reply sentiment comparison case-mismatch breaks the positive-reply webhook/state update; low-confidence replies are not routed to human review (SRS 3.13).
6. LinkedIn task auto-generation does not exist; linkedin campaigns produce email drafts.
7. Dispatch ignores lead/campaign status (stop conditions incomplete); daily-limit overflow permanently fails messages.
Status: Phases 1–7 structurally complete; pipeline requires the above fixes to actually deliver the ToFu automation goal.

## Post-Audit Remediation (2026-06-11) — System Now Functional End-to-End
All blockers from the Post-Phase 7 Independent Audit are fixed and verified (see the matching entry in `experience.md` for full detail). Highlights:
- **Scraping pipeline works:** DataCleaner bugs fixed (verified 3-emails-in -> 3-leads-out), and `trigger_scheduled_scrapes_task` (Celery Beat, every 6h) + `POST /leadsources/{id}/scrape/` finally connect Campaign/LeadSource to the scrapers. `LeadSource` gained `campaign` and `last_scraped_at` fields.
- **Company attribution is per-email-domain** (directories are no longer treated as the lead's employer); personal vs company LinkedIn links separated.
- **LinkedIn funnel is real:** AI connection-note + DM drafters (`ai_engine/linkedin_generator.py`); linkedin campaigns generate manual tasks (not email drafts); completing a connect task auto-chains the DM task.
- **Lead Magnet engine:** AI picks per-lead magnets from the catalog (`Lead.recommended_lead_magnet`); `LeadMagnetSubmission` model + endpoint track form submissions with webhook notification.
- **Activity entity** (SRS 3.9) added with full pipeline logging; **Approval Queue** now shows draft subject/body + lead context, and low-confidence reply classifications (< 0.85) are routed to it (SRS 3.13/3.15).
- **Campaign status/start/end dates now gate** scraping, drafting, dispatch, and follow-ups. Stop conditions cancel queued drafts when leads reply or are disqualified. Daily limits defer instead of failing messages. Follow-ups thread via Re: subjects + In-Reply-To/References.
- **EmailAccount** gained `smtp_encryption` (tls/ssl/none) and `imap_use_ssl`; IMAP reader rewritten (PEEK, sender fallback, bounce/NDR matching). Reply sentiment is a strict lowercase Literal. Score threshold is the `LEAD_SCORE_THRESHOLD` setting (default 70).
- **Frontend** reads the API base URL from `NEXT_PUBLIC_API_URL` (set to port 18000 in docker-compose); approvals UI renders the proposed action and lead intel.
- **Migration:** `crm/0007` (includes legacy linkedin_url dedupe). **Tests:** `manage.py check`, `tsc --noEmit`, `test_e2e_email` (outbound + inbound legs), `test_e2e_linkedin` — all passing in Docker.
Remaining known gaps (unchanged, deliberately out of scope): external API keys not connected, no API authentication, analytics endpoints still mock-data on the dashboard.

## Go-Live Runbook (2026-06-11)
A complete end-to-end deployment checklist now exists at `Docs/go-live runbook.md`. It covers: external accounts/API keys (OpenAI required; Langfuse/AdsPower/proxies/Slack optional), outreach domain + mailbox setup with SPF/DKIM/DMARC and warm-up limits, `.env` configuration, the SECRET_KEY-before-passwords caveat, stack bring-up, n8n workflow import/activation, seed-data steps (EmailAccounts, LeadMagnets, Campaign, LeadSources), the pre-launch verification sequence (E2E tests, manual scrape, approval + reply loop tests), the daily operator routine, and the security hardening checklist required before any non-local exposure.

## Scraping Engine Overhaul — BFS Crawler + Lead Quality Fixes (2026-06-12)

### Serper API fixes
- Removed all `site:` operators from Serper queries — free tier blocks them (returns 400).
- Capped `num` param to `min(limit, 10)` — free tier rejects values > 10.
- Queries now use natural language: `"Company" Persona linkedin.com/in`, `"Company" Persona email iletisim`, `"Company" kariyer.net`.
- `SEARCH_DISCOVERY_RESULT_LIMIT` env var set to `10`.

### Full-site BFS crawler (`backend/scraper/static.py`)
- Complete rewrite: replaced old "guess a few paths + contact link" strategy with a full **Breadth-First Search** site crawler.
- `_crawl_site(start_url)` maintains a **priority queue** (team/contact/staff pages first) and a normal queue; visits up to `MAX_CRAWL_PAGES = 80` pages per source.
- Pre-seeds 30 guessed Turkish/English staff paths (`/ekibimiz`, `/egitmenlerimiz`, `/team`, etc.) into the BFS so they are always attempted.
- Follows ALL internal same-domain `<a href>` links discovered on each page.
- `scrape_website()` calls `_crawl_site()` and processes contacts from every page.
- `_PRIORITY_PATH_HINTS` tuple controls which paths jump to the front of the queue.

### Non-person lead filtering (`backend/scraper/extractor.py`)
- Added `_NON_PERSON_WORDS` frozenset (~45 words: "workshop", "training", "school", "english", "want", "take", etc.).
- `_name_from_text()` now rejects any 2-3 word heading that contains a non-person word — prevents "Teacher Workshops", "Want Take", "Ialf Serpong" from being saved as leads.
- Added raw HTML regex scan for `linkedin.com/in/` URLs (step 5 in `extract_contacts`) — catches LinkedIn profile URLs embedded in JavaScript, data-attributes, or plain text that are NOT inside `<a>` tags.
- Added `_parse_staff_table()` — extracts staff from HTML `<table>` elements with name/title/email column detection; handles both header-row and header-less tables.
- Added `_parse_staff_list()` — extracts staff from `<ul>/<ol>` elements whose CSS class/id matches people/team/staff hints.
- Both new extractors are wired into `extract_contacts()` as steps 2b and 2c.

### LLM lead scoring improvement (`backend/ai_engine/lead_profiler.py`)
- `score_lead()` now accepts `lead_name` parameter.
- When a name is provided the LLM prompt explicitly instructs the model: if the name doesn't look like a real human name, give score = 0 and persona = "Non-Person / Bad Data".
- `score_lead_task` in `tasks.py` passes `lead_name = first_name + last_name` to `score_lead()`.

### Bogus lead elimination (`backend/crm/tasks.py`)
- `_search_discovered_contacts`: inaccessible non-LinkedIn pages are no longer saved as fake leads (only genuine `linkedin.com/in/` URLs are kept from inaccessible pages).
- Accessible pages: only save a profile-URL-only lead if at least a first or last name was parsed (prevents Turkish page titles like "İngilizce İlanları" being saved as a person).

### Email enrichment pipeline (NEW)
- **`backend/scraper/hunter.py`** — new module:
  - `find_email(first, last, domain, api_key)` — Hunter.io email-finder API call.
  - `domain_search(domain, api_key)` — Hunter.io domain-search (indexes all known emails for a domain).
  - `detect_email_pattern(emails)` — analyses known emails to infer naming convention (first.last, flast, etc.).
  - `infer_email(first, last, domain, api_key)` — full lookup pipeline: Hunter.io → pattern detection → fallback `firstname.lastname@domain`.
- **`enrich_lead_email_task`** (Celery task, default queue) — runs automatically for every new lead that has a name + company domain but no email.  Tries Hunter.io then pattern inference.  If email found: updates the lead, logs activity, and queues `generate_draft_task` if lead score ≥ threshold and campaign is active.
- Wired into `_process_and_save_scrape_result`: new leads with name+domain but no email auto-queue the task (countdown=15s after creation).
- Wired into the "existing lead updated" branch: if a lead gains a name from enrichment but still lacks an email, enrichment is re-queued.
- New env vars: `HUNTER_API_KEY=` (optional — pattern inference runs without it), `EMAIL_ENRICHMENT_ENABLED=true`.

### Campaign edit feature (`frontend/src/app/(dashboard)/campaigns/[id]/page.tsx`)
- `EditCampaignModal` component added inline — edits Target Persona, Target Sector, Target Country, Value Proposition via `PATCH /api/crm/campaigns/{id}/`.
- Pencil icon button in header; Target Persona and Sector info cards also clickable.

### "Mail Okumayı Simüle Et" testing button
- **Backend**: `POST /api/crm/email-accounts/poll_now/` — immediately triggers `poll_all_inboxes_task` without waiting for the 5-minute Celery Beat cycle. Added as `@action(detail=False, methods=['post'])` on `EmailAccountViewSet`.
- **Frontend**: "📨 Mail Okumayı Simüle Et" indigo button added to the Campaign Actions bar (active campaigns only).

### IMAP reply system (existing — reminder)
- `poll_all_inboxes_task` runs every 5 min via Celery Beat.
- Matches replies by `In-Reply-To`/`References` thread headers, then by sender address.
- Matched reply → `classify_reply_task` → OpenAI LLM classifies as positive/negative/out_of_office/unsubscribe/bounce.
- Positive → webhook notification; unsubscribe/bounce → lead auto-suppressed.

## Current Status (2026-06-12)
- All phases 1–7 fully implemented and end-to-end verified.
- BFS crawler operational; scrapes up to 80 pages per source site.
- Email enrichment pipeline active: named leads without email are automatically enriched via Hunter.io (if key set) or `firstname.lastname@domain` pattern inference.
- `OUTREACH_TEST_MODE=true` — all outgoing emails redirect to `burc.psikoloji@gmail.com`.
- To fully unlock the pipeline: set `HUNTER_API_KEY=<your-key>` in `.env` and restart workers.
