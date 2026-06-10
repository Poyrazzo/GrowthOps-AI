# Current State

This document serves as the single source of truth for the current state of the Growth Automation & AI Ops System. 

**Rule:** We will write and update the current system's state inside this document in any case as the system evolves.

## Architecture Status
- **Docker Compose:** Fully initialized with `postgres` (15), `redis` (7-alpine), `django`, `celery_worker`, `celery_beat`, `playwright_worker`, and `frontend` services.
- **Backend:** Django and Django REST Framework initialized in the `backend/` directory. 
  - CORS is configured to allow Next.js (`http://localhost:3000`) to fetch API data securely.
  - Celery is configured with Redis as the broker and PostgreSQL (`django-celery-results`) as the result backend.
- **CRM App:** `crm` app initialized. 
  - Core models (`Campaign`, `Company`, `LeadSource`, `Lead`)
  - Secondary models (`EmailAccount`, `LeadMagnet`, `Message`, `Reply`)
  - Utility models (`SuppressionList`, `ApprovalQueue`, `LinkedInTask`, `AuditLog`)
  All are mapped to the database and registered in the Django Admin. `Campaign` and `Lead` models have lifecycle `status` fields.
- **API Endpoints:** DRF serializers, viewsets, and a DefaultRouter are implemented. All 12 CRM models are fully exposed via REST APIs under `http://localhost:18000/api/crm/`.
- **Scraping Engine:** 
  - `StaticScraper` (`requests`/`BeautifulSoup`) is implemented for fast metadata and text extraction. It natively supports Proxy rotation.
  - `DynamicScraper` (Playwright) is implemented for heavy JS/SPA extraction. It operates from a dedicated `playwright_worker` node to protect API stability. It natively supports AdsPower profile isolation via CDP, as well as standard Proxy rotation.
  - `AdsPowerManager` is built to orchestrate starting/stopping external browser profiles for high-security scraping.
  - `DataCleaner` (Pandas) is implemented to normalize, deduplicate, and filter raw scraped leads before database insertion.
  - **Celery Orchestration** (`backend/crm/tasks.py`) connects the entire pipeline. It routes static scrapes to the standard worker and dynamic scrapes to the Playwright worker. Tasks return structured JSON dictionaries and feature exponential backoff retry mechanisms for network failures.
- **Frontend:** Next.js initialized in the `frontend/` directory with `shadcn/ui` and `TanStack Query`.
- **Current Completion:** Phase 1, Phase 2, and Phase 3 are completely finalized and architecturally hardened.
