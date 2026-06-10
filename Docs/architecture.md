# System Architecture
## Growth Automation & AI Ops System

This document outlines the full system architecture based on the defined technology stack in `stack.md`.

### 1. High-Level Architecture Overview
The system is built as a monolithic core (Django) with distributed workers (Celery/Playwright) and a modern web frontend (Next.js), orchestrated entirely via Docker Compose for local deployment.

### 2. Core Components

#### 2.1 Backend Layer (Python / Django)
- **Framework:** Django + Django REST Framework (DRF)
- **Purpose:** Core business logic, APIs, ORM, authentication, and built-in admin panel.
- **Why:** Django provides a robust ORM and admin interface out-of-the-box, which perfectly fits the CRM-heavy nature of the application.

#### 2.2 Database / CRM Layer (PostgreSQL)
- **Database:** PostgreSQL (Supabase Postgres recommended for MVP/early production, moving to local container if needed).
- **Core Entities:** `campaigns`, `companies`, `leads`, `messages`, `replies`, `activities`, `tasks`, `suppression_list`, etc.
- **Why:** Relational integrity is critical for tracking complex state transitions across campaigns and leads.

#### 2.3 Frontend / Dashboard Layer (TypeScript / Next.js)
- **Framework:** Next.js + React + TypeScript
- **Styling/UI:** Tailwind CSS, shadcn/ui, Recharts/Tremor
- **State Management & Data Fetching:** TanStack Query, React Hook Form, Zod
- **Purpose:** Admin dashboard, campaign builder, approval queue, lead database, and analytics.

#### 2.4 Scraping & Browser Automation Layer (Python)
- **Static Sites:** `requests`, `httpx`, `BeautifulSoup`, `selectolax` (faster, cheaper).
- **Dynamic Sites:** Playwright (for JS-heavy sites, infinite scroll, forms).
- **Profile Management:** AdsPower (for isolated browser environments via CDP/Local API).
- **LinkedIn Strategy:** **Human-in-the-loop only**. Generates tasks and drafts; absolutely no direct bot automation to prevent bans.

#### 2.5 AI Layer
- **Provider:** OpenAI API.
- **Mechanism:** Structured Outputs with JSON Schema to ensure strict JSON responses.
- **Validation:** Pydantic for schema validation.
- **Observability:** Langfuse or Helicone for AI logging.
- **Purpose:** Lead persona classification, scoring, message angle generation, and reply classification.

#### 2.6 Background Jobs & Orchestration
- **Internal Jobs:** Celery + Redis (broker/cache) for scraper runs, AI batches, email queues, and IMAP polling.
- **Task Scheduling:** Celery Beat.
- **External Integrations:** n8n for lightweight glue logic (Slack notifications, webhooks, simple CRM syncs).

#### 2.7 Email & Inbox Layer
- **Provider:** API-first provider like Postmark (or SendGrid).
- **Mechanism:** Outbound API for sending, inbound webhooks for receiving and parsing replies into JSON.
- **Purpose:** Managing outbound sequences, tracking bounces/unsubscribes, and feeding responses into the AI Reply Classifier.

### 3. Infrastructure & Deployment
- **Environment:** Local execution (Laptop, 16GB RAM).
- **Containerization:** Docker + Docker Compose.
- **Containers Defined:**
  - `postgres` (Database)
  - `redis` (Cache/Broker)
  - `django` (Core API backend)
  - `celery-worker` (Background tasks execution)
  - `celery-beat` (Task scheduler)
  - `playwright-worker` (Browser automation node)
  - `n8n` (Workflow automation)
  - (Frontend can be run via local Node or an additional `nextjs` container)
