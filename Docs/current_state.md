# Current State

This document serves as the single source of truth for the current state of the Growth Automation & AI Ops System. 

**Rule:** We will write and update the current system's state inside this document in any case as the system evolves.

## Architecture Status
- **Docker Compose:** Fully initialized with `postgres` (15), `redis` (7-alpine), `django`, `celery_worker`, `celery_beat`, and `frontend` services.
- **Backend:** Django and Django REST Framework initialized in the `backend/` directory. 
  - CORS is configured to allow Next.js (`http://localhost:3000`) to fetch API data securely.
  - Celery is configured with Redis as the broker and PostgreSQL (`django-celery-results`) as the result backend.
- **CRM App:** `crm` app initialized. 
  - Core models (`Campaign`, `Company`, `LeadSource`, `Lead`)
  - Secondary models (`EmailAccount`, `LeadMagnet`, `Message`, `Reply`)
  - Utility models (`SuppressionList`, `ApprovalQueue`, `LinkedInTask`, `AuditLog`)
  All are mapped to the database and registered in the Django Admin. `Campaign` and `Lead` models have lifecycle `status` fields.
- **API Endpoints:** DRF serializers, viewsets, and a DefaultRouter are implemented. All 12 CRM models are fully exposed via REST APIs under `http://localhost:18000/api/crm/`.
- **Scraping Engine:** A pure Python module (`backend/scraper/static.py`) utilizing `requests` and `BeautifulSoup` is established. It fetches metadata, visible body text, potential emails via regex, and social media links.
- **Frontend:** Next.js initialized in the `frontend/` directory with `shadcn/ui` and `TanStack Query`.
- **Current Completion:** Phase 1, Phase 2, and Phase 3 (Step 3.1) are complete.
