# External Services & Connections Directory

This document provides a comprehensive list of every external API, service, and network connection utilized by the GrowthOps AI platform. It serves as a reference for configuring your `.env` variables, setting up firewalls, and managing external credentials.

---

## 1. AI & Machine Learning Services

### **OpenAI API**
- **Purpose**: Powers the core Large Language Model (LLM) engine for the system. Used for drafting hyper-personalized outreach emails, analyzing lead data, and classifying incoming replies (e.g., detecting "positive" vs "bounce").
- **Connection Type**: Outbound REST API via `langchain_openai`.
- **Environment Variables Required**:
  - `OPENAI_API_KEY`: Your secret key from the OpenAI Developer Platform.
- **URL**: `https://api.openai.com/v1/`

### **Langfuse (LLM Observability)**
- **Purpose**: Provides deep tracing, prompt management, and analytics for every LLM call made by the system. Helps you monitor token costs and debug LLM logic.
- **Connection Type**: Outbound REST API via `langfuse`.
- **Environment Variables Required**:
  - `LANGFUSE_PUBLIC_KEY`: Your Langfuse project public key.
  - `LANGFUSE_SECRET_KEY`: Your Langfuse project secret key.
  - `LANGFUSE_HOST`: The host URL (defaults to `https://cloud.langfuse.com` but can be pointed to a self-hosted instance).

---

## 2. Scraping & Automation Services

### **AdsPower Local API**
- **Purpose**: An anti-detect browser orchestrator used to execute safe, stealthy LinkedIn outreach. GrowthOps AI communicates with the local AdsPower daemon to spin up isolated browser profiles with unique fingerprints.
- **Connection Type**: Local HTTP API.
- **Environment Variables Required**:
  - `ADSPOWER_API_URL`: The URL of your local AdsPower daemon (defaults to `http://host.docker.internal:50325` for Docker environments).
- **URL**: `http://local.adspower.net:50325` (Default)

### **External Proxy Networks (Optional but Recommended)**
- **Purpose**: Used by the LinkedIn scraper/automator to rotate IP addresses and prevent account bans.
- **Connection Type**: HTTP / SOCKS5 proxies dynamically assigned to Playwright browser contexts.
- **Configuration**: Configured per campaign or per scraper session dynamically.

---

## 3. Communication Providers

### **Custom SMTP Servers (Email Sending)**
- **Purpose**: The infrastructure used to physically dispatch outbound email campaigns.
- **Connection Type**: SMTP / SMTPS (Ports: `587`, `465`, `25`).
- **Configuration**: Managed dynamically via the `EmailAccount` database model. Users input their specific host, port, username, and encrypted password directly into the CRM. GrowthOps AI supports any standard SMTP provider (Google Workspace, Outlook, AWS SES, Mailgun, SendGrid, etc.).
- **Mock Fallback**: Defaults to `greenmail` on port `3025` for local testing environments without TLS.

### **Custom IMAP Servers (Reply Parsing)**
- **Purpose**: Connects to the user's inbox to read incoming emails, allowing the system to detect replies and feed them into the AI classification engine.
- **Connection Type**: IMAP / IMAPS (Ports: `993`, `143`).
- **Configuration**: Managed dynamically via the `EmailAccount` database model.

---

## 4. Internal Orchestration & Infrastructure

### **n8n Workflow Automation**
- **Purpose**: Handles dynamic event routing and third-party integrations (like sending a Slack alert when a lead replies positively). It serves as the bridge between GrowthOps AI's internal logic and your external business tools.
- **Connection Type**: Internal Webhooks & Docker Networking.
- **Configuration**:
  - GrowthOps AI sends POST requests to `http://n8n:5678/webhook/growthops-events` (or a custom `WEBHOOK_URL`).
  - **Downstream Integrations**: From n8n, you can visually connect to external services like **Slack**, **Discord**, **HubSpot**, or **Salesforce** (e.g., using the `Slack_Notification_Template.json`).
- **Dashboard URL**: `http://localhost:5678`

### **PostgreSQL Database**
- **Purpose**: The primary persistence layer for CRM data, campaign states, and immutable audit logs.
- **Connection Type**: TCP (Port: `5432`).
- **Internal URL**: `postgres://admin:adminpassword@postgres:5432/growthops`

### **Redis Message Broker**
- **Purpose**: Powers the Celery task queues. Handles asynchronous background jobs like bulk email dispatching, browser automation scraping, and LLM reply classification.
- **Connection Type**: TCP (Port: `6379`).
- **Internal URL**: `redis://redis:6379/0`

---

## 5. Local Port Bindings (For Operator Access)

For local development and monitoring, the system binds the following ports to your host machine:

- **Next.js Frontend (Operator Dashboard)**: `http://localhost:3000`
- **Django REST API Backend**: `http://localhost:8000` (Mounted at `/api/crm/`)
- **n8n Automation Dashboard**: `http://localhost:5678`
- **GreenMail Mock Server UI**: `http://localhost:8080/api/mail`
