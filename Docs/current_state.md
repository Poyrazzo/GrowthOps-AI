# Current State

This document serves as the single source of truth for the current state of the Growth Automation & AI Ops System. 

**Rule:** We will write and update the current system's state inside this document in any case as the system evolves.

## Architecture Status
- **Docker Compose:** Fully initialized with `postgres` (15), `redis` (7-alpine), `django`, `celery_worker`, `celery_beat`, `playwright_worker`, and `frontend` services.
- **Backend:** Django and Django REST Framework initialized in the `backend/` directory. 
- **CRM App:** Core models, secondary models, and utility models (`SuppressionList`, `EmailAccount`, `AuditLog`, etc.) are fully mapped to Postgres and exposed via DRF.
- **Scraping Engine:** Fully functional static (`requests`) and dynamic (`Playwright`) scrapers with proxy support, AdsPower isolation, and Pandas data normalization.
- **AI Enrichment & Classification:** Fully autonomous Celery pipeline: Scrape -> Clean -> Save Leads -> Enrich Company -> Score Leads -> Draft Emails. Guarded against infinite loops and uniquely constrained to save OpenAI tokens via Langfuse.
- **Outreach Engine (Phase 5):**
  - **Security:** Integrated `cryptography` (Fernet) to securely encrypt `EmailAccount` passwords via Django's `SECRET_KEY`.
  - **SMTP Sender:** Implemented `backend/outreach/smtp.py` with suppression list checking and Thread ID tracking.
  - **IMAP Reader:** Implemented `backend/outreach/imap.py` with scheduled Celery Beat polling to match incoming replies using metadata headers.
  - **AI Reply Classification:** Implemented `backend/ai_engine/reply_classifier.py`. Incoming replies are instantly chained to a `gpt-4o-mini` classification pipeline.
  - **Autonomous Suppression Loop:** If the AI classifies a reply as `unsubscribe` or `bounce`, the system autonomously blocks the lead by inserting them into the `SuppressionList` and disqualifying them in the CRM.
  - **Sequence Manager:** Implemented `backend/outreach/sequence.py`. A background task `dispatch_emails_task` runs every 10 minutes to explicitly sweep the database for pending drafts and send them. A second background task `process_followups_task` runs every hour, analyzing all leads `in_sequence` and invoking the AI to write and append a contextual follow-up email if no reply has been received in 3 days (max 3 emails per sequence).
- **Frontend:** Next.js initialized in the `frontend/` directory with `shadcn/ui` and `TanStack Query`.
- **Current Completion:** Phase 1, Phase 2, Phase 3, Phase 4, and Phase 5 (Steps 5.1, 5.2, 5.3, and 5.4) are completely finished.
