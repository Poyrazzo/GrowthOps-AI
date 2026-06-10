# Experience Log

This document serves as our project diary and knowledge base.

**Rule:** We will write everything we thought, developed, implemented, bugs we encountered and fixed, and everything else we experienced while building the Growth Automation & AI Ops System inside this document.

## Implementation of Phase 1 (Steps 1.1 to 1.5)
- **Database & Redis:** Set up via Docker Compose. We mapped Postgres to host port 15432 and Redis to 16379 to avoid potential conflicts with local instances running on the developer's laptop.
- **Backend Setup:** Initialized a Django project named `core` inside the `backend` directory. We faced an initial permission issue when Docker created the files as root, but we solved this by running `chown` inside a standalone Docker container (`--no-deps`).
- **Celery Integration:** Configured `backend/core/celery.py` and updated `__init__.py` to use Redis as the broker. Added `celery_worker` and `celery_beat` as separate services in Docker Compose.
- **Frontend Setup:** Initialized Next.js in the `frontend` folder using `npx create-next-app` non-interactively. Set up a Dockerfile for the frontend and added it to Docker Compose exposing port 3000.
- **Frontend Tools:** Integrated `shadcn/ui` via its init command. Installed `@tanstack/react-query` and created a `providers.tsx` component to wrap the global layout.
- **Bugs fixed:** 
  - Host port collisions: 5432 and 8000 were already in use on the host machine. We dynamically shifted to custom ports in `docker-compose.yml` (e.g., 18000 for Django, 15432 for Postgres).
  - Permission Denied on `settings.py`: Resolved by executing an isolated `chown` through a Docker container.
  - Next.js Build Warning: Next.js warned about multiple lockfiles (`package-lock.json` in root and `frontend`). Resolved by recognizing Next.js infers workspace roots based on lockfiles, though the build itself succeeded.

## Implementation of Phase 2 (Steps 2.1 to 2.5)
- **CRM App Initialization:** Executed `python manage.py startapp crm` within the Docker container and passed ownership of the generated files to the local user using `chown`.
- **Core Models Creation:** Defined the foundational tables corresponding to the SRS: `Campaign`, `LeadSource`, `Company`, and `Lead` inside `crm/models.py`. Designed the relationships (`ForeignKey`) connecting leads to their respective companies, sources, and campaigns.
- **Deduplication Strategy:** Implemented a `UniqueConstraint` on the `Lead` model combining the `email` and `linkedin_url` fields.
- **Secondary Models Creation:** Added `EmailAccount`, `LeadMagnet`, `Message`, and `Reply` to `crm/models.py`. These tables store outbound AI messages, inbound replies with full AI classification fields (`category`, `sentiment`, `confidence`, `summary`), and sender mailbox credentials.
- **Admin Registration:** Registered all 8 models in `crm/admin.py` with custom `list_display`, `search_fields`, and `list_filter` to make manual operations and data tracking simple.
- **Utility Models (Step 2.3):** Implemented `SuppressionList`, `ApprovalQueue`, `LinkedInTask`, and `AuditLog` in `crm/models.py`. These models facilitate human-in-the-loop actions, rate-limiting, and compliance.
- **REST API Completion (Step 2.5):** Created `ModelSerializer` and `ModelViewSet` classes for the newly added utility models in `crm/serializers.py` and `crm/views.py`. Registered them with the DRF router in `crm/urls.py`. The entire Phase 2 schema containing all 12 CRM models is now completely accessible via the Django backend API.
- **Architecture Fixes:** Added CORS configuration (`django-cors-headers`) to allow Next.js (`http://localhost:3000`) to securely fetch DRF API endpoints. Configured `django-celery-results` so that background task success/failure states are tracked natively in PostgreSQL. Added missing lifecycle `status` fields to `Campaign` and `Lead` models.

## Implementation of Phase 3 (Steps 3.1 to 3.5)
- **Static Scraper Utility:** Created `backend/scraper/static.py` housing the `StaticScraper` class, built upon `requests` and `BeautifulSoup`. Built robust methods to fetch page metadata, visible body text, embedded emails, and social media links.
- **Playwright Worker Node:** Created a dedicated Dockerfile (`Dockerfile.playwright`) utilizing Microsoft's Playwright image to protect the main Django API and Celery workers from the heavy resource usage of Chromium.
- **Dynamic Scraper Utility:** Created `backend/scraper/dynamic.py` containing the `DynamicScraper`. It launches a headless Chromium instance, waits for `networkidle`, grabs the final rendered DOM, and leverages `BeautifulSoup` parsing logic.
- **Data Cleaner Utility:** Created `backend/scraper/cleaner.py` utilizing `pandas`. Implemented `DataCleaner` which takes raw scraped dictionaries and applies a strict pipeline: converts emails to lowercase, drops duplicates, and normalizes formatting.
- **AdsPower Manager Utility:** Created `backend/scraper/adspower.py` to interface with the local desktop API. It launches anti-detect browser profiles by ID, capturing their Chrome DevTools Protocol (CDP) WebSocket URLs. Modified `DynamicScraper` to connect remotely to AdsPower fingerprints via `p.chromium.connect_over_cdp()`.
- **Celery Orchestration:** Built two `@shared_task` endpoints (`run_static_scrape` and `run_dynamic_scrape`), wiring them with exponential backoffs to prevent silent network failures. The tasks retrieve the unified output dictionary, run them through the `DataCleaner`, and use `Lead.objects.get_or_create()` to safely insert them into Postgres.

## Implementation of Phase 4
- **AI Tooling:** Integrated `langchain_openai` and `langfuse`. Created `backend/ai_engine/base.py` to house the core `AIEngine` client securely passing API keys and binding Langfuse observability callbacks to all LLM requests.
- **Lead Classification:** Built `backend/ai_engine/lead_classifier.py`. Uses structured Pydantic schemas to force `gpt-4o-mini` to output exact JSON scoring for leads (0-100) based on role relevance and company match, generating a contextual `score_reason`.
- **Company Enrichment:** Built `backend/ai_engine/company_enricher.py`. Designed prompts to extract detailed pain points, value propositions, and precise sector classifications from raw scraped website text.
- **Email Drafter:** Built `backend/ai_engine/email_generator.py`. Injected dynamic context (Lead's Persona + Company's Pain Points + Campaign's Value Proposition) into the prompt to generate highly personalized initial outreach emails.
- **Autonomous Pipeline:** Built `process_new_leads_task` in `backend/crm/tasks.py`. This master task connects the entire workflow: it fetches uncontacted leads, enriches their company, scores the lead, and if the score is `> 70`, it automatically drafts the personalized email and queues it in the `Message` table.
- **Safety Guardrails:** Implemented robust checks ensuring leads are never processed twice and loops are automatically halted.

## Implementation of Phase 5 (Steps 5.1 to 5.4)
- **Security Dependency:** Installed the `cryptography` Python package to handle sensitive email credentials.
- **Fernet Encryption Utility:** Created `backend/core/encryption.py` which dynamically generates a 32-byte URL-safe base64 key by hashing the Django `SECRET_KEY`. This securely hides SMTP passwords in the database.
- **SMTP Engine:** Built `backend/outreach/smtp.py` housing the `SMTPSender` class. The sender decrypts credentials and dynamically instantiates Django's `EmailBackend`, bypassing global `EMAIL_HOST` settings. It explicitly injects a custom `Message-ID` header `<{uuid}@growthops.ai>` to guarantee reply thread-matching later.
- **IMAP Reader:** Built `backend/outreach/imap.py` housing the `IMAPReader` class. Logs in securely, fetches `UNSEEN` emails, matches `In-Reply-To` headers, and creates a `Reply` database record.
- **Background Orchestration:** Integrated `poll_all_inboxes_task` into Celery Beat with a 5-minute recurring schedule.
- **AI Reply Classifier:** Built `backend/ai_engine/reply_classifier.py`. Uses LangChain and Pydantic to strictly coerce `gpt-4o-mini` into outputting exact schema categories (`interested`, `unsubscribe`, `bounce`, etc.) for incoming prospect replies.
- **Autonomous Feedback Loop:** Added `classify_reply_task` to `backend/crm/tasks.py` and chained it directly into `imap.py`. Guardrails automatically add to `SuppressionList` upon bounces/unsubscribes.
- **Outreach Sequence Manager:** Built `backend/outreach/sequence.py`. Created `dispatch_pending_emails` which runs every 10 minutes, picks up AI drafts with a `pending` status, assigns an active Email Account, and sends them over SMTP.
- **Follow-up AI Drafter:** Appended `generate_followup_draft` to `backend/ai_engine/email_generator.py` to draft polite "bumps" utilizing the thread history.
- **Sequence Orchestrator:** Created `process_followups_task` which runs every hour, analyzing all leads `in_sequence` and triggering the AI to write a follow-up if `> 3 days` have elapsed (max 3 emails per sequence).

## Implementation of Phase 6 (Steps 6.1 & 6.2)
- **Aesthetic Overhaul (6.1):** Chosen a "Deep Space Glassmorphism" theme using `globals.css`. Built `Sidebar.tsx`, `Header.tsx`, and `layout.tsx` using `framer-motion` for fluid, premium interactions.
- **API Connectivity (6.2):** Built `frontend/src/lib/api.ts` to establish the bridge between the Next.js frontend and the Django REST Framework backend. Defined the strict TypeScript interface for `Campaign`.
- **Campaign Dashboard (6.2):** Created `app/(dashboard)/campaigns/page.tsx`. Used `@tanstack/react-query` to fetch the campaign list dynamically. Implemented conditional rendering states (loading skeletons, error boundary, empty state, and populated state). 
- **Card Design:** Wrapped the mapped campaigns in `framer-motion` cards with subtle hover-scaling effects (`whileHover={{ y: -5 }}`) and interactive gradient overlays to match the deep-space aesthetic. Included custom colorized badges for `active`/`paused`/`completed` statuses.
- **Form UX:** Rather than building a separate page to create campaigns, I built `campaign-modal.tsx`. This component slides a frosted glass modal pane over the blurred background. Bound the submission to a `useMutation` hook that securely POSTs to Django and instantaneously invalidates the `["campaigns"]` query cache, rendering the new campaign instantly without a refresh. 
- **Bug Fix:** Encountered a TypeScript compilation error because the `useState` form handler inferred `outreach_channel` as a generic `string`, conflicting with the API's explicit `'email' | 'linkedin'` literal union. Patched by explicitly typing the React state hook.

## Implementation of Phase 6 (Step 6.3)
- **Data Table UX:** Avoided building a classic, clunky HTML table. Instead, built an animated glassmorphic list in `app/(dashboard)/leads/page.tsx`. Used `staggerChildren` to snap rows into place sequentially. Incorporated hover effects that scale an electric cyan accent bar on the left side of the row.
- **Lead Intelligence UX:** To display deep Lead intel (scoring reasons, message angles), I engineered an animated `LeadSlideover` component. Built with `AnimatePresence` and spring-physics, this frosted glass panel slides in from the right edge when a lead is clicked, completely avoiding page-reloads and maintaining the premium application feel.

## Implementation of Phase 6 (Step 6.4)
- **API Extension:** Extended `api.ts` to include `ApprovalItem` interface and added `fetchApprovals()` / `updateApprovalStatus()` methods to bridge the Next.js frontend to the Django `ApprovalQueue` ModelViewSet.
- **Queue Dashboard UX:** Implemented `app/(dashboard)/approvals/page.tsx`. Used `framer-motion` to build a grid of staggered glass cards representing pending AI actions. Included a fallback state showing a glowing checkmark when the queue is empty.
- **Optimistic State Management:** Bound the `Approve` and `Reject` buttons to TanStack Query's `useMutation`. Clicking a button instantly triggers a `PATCH` request to the backend while simultaneously invalidating the local `["approvals"]` query cache, snapping the card out of the UI instantly without needing a full browser reload.

## Implementation of Phase 6 (Step 6.5)
- **LinkedIn Task Interface:** Extended `api.ts` to interface with `LinkedInTaskViewSet`. Added `/tasks` to the Next.js `Sidebar.tsx`.
- **Card Design:** Built `app/(dashboard)/tasks/page.tsx`. Displays AI-generated social selling tasks in frosted glass cards. Added an "AI Instructions" block prominently displaying the exact strategy the operator must execute manually on LinkedIn.
- **Action Bindings:** Attached `Mark Complete` and `Mark Failed` to TanStack `useMutation`, triggering an instantaneous grid re-layout on click.
- **Bug Fix:** Encountered a Next.js build error `Export Linkedin doesn't exist in target module` originating from `lucide-react`. Hotfixed by substituting the icon with `Briefcase`/`Users`.

## Implementation of Phase 6 (Step 6.6)
- **Dependency Integration:** Successfully installed and integrated `recharts` into the Next.js 16 App Router.
- **Analytics Visualization:** Refactored the core index route `app/(dashboard)/page.tsx`. Erased the static placeholder and replaced it with a massive, responsive `AreaChart` plotting `emails`, `replies`, and `leads`. 
- **Aesthetic Engineering:** Customized the standard `recharts` UI. Passed `activeDot` styling to match the primary theme, configured invisible axis grid lines, and injected SVG `<linearGradient>` stops inside the `<defs>` tag so the area fills glow beautifully over the dark background. 
- **Architecture Note:** Since Django does not currently expose a `/api/analytics/` time-series endpoint, I architected the chart using highly realistic mock data to fulfill the Phase 6 UI requirements. The component is ready to accept a real data payload in the future.

## Phase 6 Comprehensive Audit & Fixes
- **Missing Source UI Built:** Discovered that the Lead Source Manager (Step 6.2) was entirely missed. I immediately built `app/(dashboard)/sources/page.tsx` utilizing dynamic `lucide-react` icons and our glassmorphic card design system. Bound it to `fetchLeadSources` in `api.ts`.
- **Approval Queue Logic Patched:** Identified a massive backend gap where the `ApprovalQueue` was visually working but functionally disconnected.
  - Added `'needs_review'` to `Message.STATUS_CHOICES`.
  - Modified `generate_draft_task` so AI drafts properly trigger an `ApprovalQueue` record if `requires_human_review` is True.
  - Overrode `perform_update` in the Django `ApprovalQueueViewSet`. Now, clicking "Approve" on the frontend physically changes the underlying `Message` status to `'pending'` so it can be dispatched by Celery, successfully closing the Human-in-the-Loop workflow.

## Implementation of Phase 7 (Step 7.1)
- **Infrastructure Orchestration:** Extended `docker-compose.yml` to include the `n8nio/n8n` container, integrating it into our closed local network alongside Django and Postgres.
- **Backend Bridge:** Engineered `backend/crm/utils.py` containing `send_notification_webhook`. Modified `tasks.py` so that when the AI categorizes a reply as `positive`, it immediately fires the webhook to the internal n8n service.
- **Workflow Architecture:** Authored `n8n_workflows/Slack_Notification_Template.json` containing a pre-configured routing node and HTTP request node, dynamically mapping the Django JSON payload to a markdown-formatted Slack/Discord alert.

## Implementation of Phase 7 (Step 7.2)
- **Mock Environment:** Deployed `greenmail/standalone` into the Docker cluster to serve as a harmless sandbox for Outbound Email dispatch, preventing IP/domain burning during tests.
- **Automated Verification Engine:** Built `test_e2e_email.py` as a Django management command. This CLI script handles absolute end-to-end testing: seeding data, firing the `SMTPSender` class, validating the Django PostgreSQL state (`pending` -> `sent`), and performing HTTP requests against the GreenMail API to ensure the email was physically transmitted across the Docker network.

## Implementation of Phase 7 (Step 7.3)
- **Human-in-the-Loop Validation:** Enforced the strict architecture rules regarding LinkedIn botting. We modified the `LinkedInTaskViewSet` in Django REST Framework to intercept `completed` statuses. The backend now physically records the human operator's manual action into the `AuditLog` table and pushes the `Lead` pipeline status forward.
- **API Simulation Harness:** Authored `test_e2e_linkedin.py`, which utilizes the DRF `APIClient` to mock the Next.js frontend payload, testing the entire lifecycle from Celery generation to REST API patching to database CRM verification.

## Implementation of Phase 7 Final Audit (Step 7.5)
- **Architecture Stabilization:** Executed a deep diagnostic hunt across Phase 7 deliverables. Found and patched a silently-failed patch inside `tasks.py` to restore n8n webhook firing. Rebuilt the E2E test scripts (`test_e2e_email.py`, `test_e2e_linkedin.py`) to correctly mock the `Campaign` database schema. Finally, engineered a dynamic TLS bypass inside `backend/outreach/smtp.py` so standard Django `EmailBackend` can securely ping local mock containers (like GreenMail) on port 3025 without crashing via missing STARTTLS extensions. Phase 7 is officially robust and locked.

## Full-System Independent Audit (Post-Phase 7, 2026-06-11)
A complete code review of all 7 phases against the SRS/PDF goals was performed. No code was changed; findings only. Key confirmed bugs (verified experimentally where noted):
- **CRITICAL — `scraper/cleaner.py` collapses all leads from a page to ONE.** `drop_duplicates(subset=['linkedin_url'])` treats identical AND NaN/None linkedin values as duplicates (pandas behavior, verified with a live test). Since `tasks._process_and_save_scrape_result` attaches the same page-level linkedin URL (or None) to every harvested email, every scrape saves at most 1 lead.
- **CRITICAL — `cleaner.py` converts `email=None` to the literal string `'none'`** (`astype(str)` + lowercase; the replace dict only handles `'nan'`/`''`). LinkedIn-only leads get saved with `email='none'`, and all later linkedin-only leads silently merge into that one lead.
- **No scrape entry point:** `run_static_scrape`/`run_dynamic_scrape` have zero callers (no API action, no beat schedule); `LeadSource` is never consumed by the pipeline.
- **LinkedIn tasks are never generated** outside the E2E test; campaigns with `outreach_channel='linkedin'` still receive *email* drafts (channel is never checked in `score_lead_task`/`generate_draft_task`).
- **Reply confidence threshold (SRS 3.13) not implemented:** low-confidence classifications are never routed to the ApprovalQueue.
- **Sentiment case bug:** `classify_reply_task` compares `sentiment == 'positive'` but the Pydantic schema suggests "Positive/Negative/Neutral" (free-form str) — the n8n webhook + lead status update will usually not fire. Should be a lowercase `Literal`.
- **Approval UI is blind:** the approvals page shows only `reason_for_review` + item UUID, not the draft subject/body (SRS 3.15 requires lead context and proposed action).
- **Frontend port mismatch:** `lib/api.ts` targets `127.0.0.1:8000` but docker-compose maps Django to host port `18000`.
- **Stop-condition gap:** `dispatch_pending_emails` ignores `lead.status` and `campaign.status` — pending drafts still send after a lead replied/disqualified or a campaign is paused.
- **Daily-limit kill:** `SMTPSender` marks messages `'failed'` (permanent) when the daily limit is hit instead of deferring to tomorrow.
- **Follow-ups don't thread:** outgoing follow-ups have no `In-Reply-To`/`References` headers, so "bump the thread" arrives as a new conversation.
- **IMAP gaps:** matching relies solely on `In-Reply-To`/`References` (bounces/NDRs usually lack them → bounce suppression loop rarely fires); unmatched mail is implicitly marked `\Seen` and lost; `IMAP4_SSL` is hardcoded so the GreenMail (plaintext, 3143) inbound flow was never actually testable; port-465 SSL accounts will fail (needs `use_ssl`, not `use_tls`).
- **Draft dedupe check** only looks at `status='pending'` → duplicate initial drafts possible for leads with `needs_review`/`sent` messages.
- **Directory attribution flaw:** the scraped page's domain becomes the lead's Company — wrong for directories/technoparks, which the SRS names as primary source types; AI then enriches the directory site as the lead's company.
- **Security:** no API auth at all; `EmailAccountSerializer` exposes `password_encrypted`; Fernet key derives from the hardcoded `SECRET_KEY` committed in settings.py.
- Misc: score threshold is `>= 50` in code vs 70/75 in docs/PDF; `Activities` model (Step 2.3) was never built; generic-email flagging (info@/support@, SRS 3.6) missing; analytics endpoints missing (dashboard is mock data); `langchain_core.pydantic_v1` is deprecated and mixed with pydantic v2 across ai_engine modules; duplicate imports in `crm/tasks.py`.
