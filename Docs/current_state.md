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
  - **SMTP Sender:** Implemented `backend/outreach/smtp.py`. The `SMTPSender` utility can accept pending AI messages, dynamically connect to custom SMTP providers (Google, Outlook, Postmark), and dispatch the email.
  - **Tracking & Suppression:** The `SMTPSender` natively checks the `SuppressionList` before sending, aborting if the lead is blocked. It explicitly injects a custom `Message-ID` header `<{uuid}@growthops.ai>` to guarantee reply thread-matching later.
  - **Audit Logging:** Emits detailed database records into `AuditLog` upon send success, failure, or suppression.
- **Frontend:** Next.js initialized in the `frontend/` directory with `shadcn/ui` and `TanStack Query`.
- **Current Completion:** Phase 1, Phase 2, Phase 3, Phase 4, and Phase 5 (Step 5.1) are completed.
