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

## Implementation of Phase 2 (Steps 2.1 and 2.2)
- **CRM App Initialization:** Executed `python manage.py startapp crm` within the Docker container and passed ownership of the generated files to the local user using `chown`.
- **Core Models Creation:** Defined the foundational tables corresponding to the SRS: `Campaign`, `LeadSource`, `Company`, and `Lead` inside `crm/models.py`. Designed the relationships (`ForeignKey`) connecting leads to their respective companies, sources, and campaigns.
- **Deduplication Strategy:** Implemented a `UniqueConstraint` on the `Lead` model combining the `email` and `linkedin_url` fields.
- **Secondary Models Creation:** Added `EmailAccount`, `LeadMagnet`, `Message`, and `Reply` to `crm/models.py`. These tables store outbound AI messages, inbound replies with full AI classification fields (`category`, `sentiment`, `confidence`, `summary`), and sender mailbox credentials.
- **Admin Registration:** Registered all 8 models in `crm/admin.py` with custom `list_display`, `search_fields`, and `list_filter` to make manual operations and data tracking simple.
- **Migrations:** Successfully generated and applied migrations to the Postgres database container.

## Implementation of Phase 2 (Steps 2.3, 2.4, and 2.5)
- **Utility Models (Step 2.3):** Implemented `SuppressionList`, `ApprovalQueue`, `LinkedInTask`, and `AuditLog` in `crm/models.py`. These models facilitate human-in-the-loop actions, rate-limiting, and compliance.
- **Admin Registration (Step 2.4):** Registered the utility models in `crm/admin.py`, configuring specialized `list_display`, `list_filter`, and `search_fields` to give operators total control over the database right out of the box.
- **REST API Completion (Step 2.5):** Created `ModelSerializer` and `ModelViewSet` classes for the newly added utility models in `crm/serializers.py` and `crm/views.py`. Registered them with the DRF router in `crm/urls.py`. The entire Phase 2 schema containing all 12 CRM models is now completely accessible via the Django backend API.
- **Migrations:** Ran `makemigrations` and `migrate` inside the Django container, applying all new tables securely to the running Postgres database.

## Phase 2.5 (Architecture Fixes)
- **CORS Configuration:** Installed `django-cors-headers` and configured `CORS_ALLOWED_ORIGINS` to accept requests from `http://localhost:3000`. This officially enables our Next.js dashboard to securely fetch our DRF API endpoints without browser policy blocks.
- **Celery Results Backend:** Installed `django-celery-results` and configured it in `settings.py` (`CELERY_RESULT_BACKEND = 'django-db'`). This ensures all scraping and AI background tasks we build in the future will have their success/failure states tracked natively in the PostgreSQL database.
- **Model Status Fixes:** Added missing `status` fields to `Campaign` (Draft, Active, Paused, Completed) and `Lead` (Uncontacted, In Sequence, Replied, Disqualified). These lifecycle states are critical for the Outreach Engine. Migrations were successfully applied.

## Implementation of Phase 3 (Step 3.1)
- **Static Scraper Utility:** Created `backend/scraper/static.py` housing the `StaticScraper` class, built upon `requests` and `BeautifulSoup`.
- **Extraction Capabilities:** Built robust methods to fetch page metadata (Title, OpenGraph Description), visible body text (stripping heavy HTML/CSS to save AI token bandwidth), embedded emails (via regex deduplication), and social media links.
- **Verification:** Successfully executed the class against `example.com` inside the Django container, returning perfectly cleaned JSON mapping.
