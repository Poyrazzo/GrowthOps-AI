# Software Requirements Specification (SRS)
## Growth Automation & AI Ops System

### 1. Introduction
#### 1.1 Purpose
This Software Requirements Specification (SRS) document describes the requirements, architecture, and functionalities of the "Growth Automation & AI Ops System". This system is an end-to-end platform designed to automate lead generation, data enrichment, personalized outreach, and response management across multiple channels (Email, LinkedIn) while ensuring compliance and human-in-the-loop safety mechanisms.

#### 1.2 Scope
The system is not just a simple lead scraping tool. It is a comprehensive growth automation platform capable of targeting various sectors (tech, health tourism, export SMEs, universities). It handles data collection, cleaning, AI-based scoring, lead magnet distribution, outreach sequencing, reply classification, and CRM integration.

### 2. Overall Description
#### 2.1 Product Perspective
The system operates as an orchestration layer connecting various data sources, browser automation tools, AI models, and communication protocols (SMTP/IMAP). It integrates with external tools like Playwright, AdsPower, OpenAI/LLMs, and workflow automation platforms (n8n/Make).

#### 2.2 User Characteristics
Primary users are Growth Teams, Sales Teams, and HR/Talent Acquisition professionals who require automated, high-quality lead generation and management without dealing with the technical complexities of scraping or AI prompt engineering.

### 3. Functional Requirements

The system is composed of 18 core modules.

#### 3.1 Segment & Campaign Planner
- The system MUST allow users to create and manage targeted campaigns.
- Each campaign MUST include `campaign_id`, `campaign_name`, `target_sector`, `target_country`, `target_persona`, `value_proposition`, `lead_magnet`, `outreach_channel`, `success_metric`, `start_date`, and `end_date`.

#### 3.2 Lead Source Finder
- The system MUST define and store data sources specific to target segments (e.g., technoparks, university directories, career pages).
- Sources MUST be recorded with `source_url`, `source_type`, `sector`, `expected_data_fields`, `access_rules`, and `priority_score`.

#### 3.3 Scraping & Browser Automation Engine
- The system MUST extract data (email, name, title, department, company, LinkedIn URL) from specified sources.
- For static sites, basic request tools (e.g., BeautifulSoup) MUST be used.
- For dynamic (JavaScript-heavy) sites, the system MUST utilize Playwright for DOM interaction, scrolling, and form handling.
- Every lead MUST be strictly tied to a `source_url` for verification.

#### 3.4 AdsPower Profile Manager
- The system MUST use AdsPower (or similar) to isolate browser profiles, cookies, local storage, and proxies for different campaigns and test environments.
- Playwright MUST connect to these isolated profiles for execution.
- The system MUST NOT perform unauthorized automated bot activities on platforms strictly prohibiting them (e.g., LinkedIn).

#### 3.5 Proxy & Session Management Layer
- The system MUST manage proxies and sessions for stability, geographic access, and IP reputation.
- It MUST log requests and implement rate limiting, timeouts, retries, and backoff mechanisms.
- Blocked domains MUST trigger a fallback to manual human review.

#### 3.6 Data Cleaning Module
- The system MUST process raw scraped data (using Pandas or similar).
- It MUST normalize emails, remove duplicates, and flag generic emails (info@, support@).
- Deduplication MUST utilize combined fields (email, LinkedIn URL, phone, name+company).

#### 3.7 AI Enrichment Module
- The system MUST analyze cleaned lead data using AI to determine persona, sector, decision-maker status, and potential needs.
- The AI MUST output structured JSON containing: `persona`, `sector`, `department`, `lead_score` (0-100), `score_reason`, `recommended_message_angle`, `recommended_lead_magnet`, and `requires_human_review`.

#### 3.8 Lead Magnet Engine
- The system MUST match leads with appropriate lead magnets (e.g., "Free HR English Analysis", "Export Sales Simulation") based on persona.
- It MUST track lead magnet form submissions and trigger CRM updates and follow-ups.

#### 3.9 CRM / Database Layer
- The system MUST serve as the central source of truth, tracking all data.
- Core entities include: `campaigns`, `companies`, `leads`, `messages`, `replies`, `activities`, `lead_magnets`, and `suppression_list`.

#### 3.10 Outreach Sequence Manager
- The system MUST manage multi-step outreach flows tailored per campaign.
- It MUST enforce stop conditions automatically (e.g., halt sequence if reply is received, unsubscribed, or bounced).

#### 3.11 SMTP Mail Sender
- The system MUST send emails to approved leads via SMTP.
- It MUST support SPF, DKIM, and DMARC compliance.
- It MUST track `sent_at`, `sender_email`, `recipient_email`, `subject`, `body`, and `message_id`.

#### 3.12 IMAP Inbox Reader
- The system MUST periodically check connected inboxes via IMAP.
- It MUST match incoming replies to existing leads using email addresses and thread history.

#### 3.13 AI Reply Classifier
- The system MUST use AI to classify incoming replies into categories: `interested`, `not_interested`, `meeting_request`, `price_question`, `unsubscribe`, `bounce`, `wrong_person`, etc.
- Output MUST be structured JSON including `category`, `sentiment`, `confidence`, `summary`, and `next_action`.
- If confidence is below a threshold (e.g., 0.85), the reply MUST be routed to the Human Approval Queue.

#### 3.14 LinkedIn Workflow Manager
- The system MUST facilitate LinkedIn outreach through a **Human-in-the-Loop** workflow, avoiding direct bot automation.
- It MUST generate AI connection requests and DM drafts.
- It MUST create tasks for users to execute manually on LinkedIn and update the CRM upon completion.

#### 3.15 Human Approval Queue
- The system MUST require human approval for critical actions (e.g., first-time emails, low-confidence AI classifications, meeting requests).
- The UI MUST display the lead context, AI summary, confidence score, and proposed action.

#### 3.16 Workflow / Automation Orchestrator
- The system MUST orchestrate complex multi-step workflows.
- It MAY utilize tools like n8n/Make for webhook management, Slack notifications, and CRM state updates, while Python handles heavy data processing.

#### 3.17 Reporting & Analytics Module
- The system MUST calculate and report key metrics: `reply_rate`, `positive_reply_rate`, `meeting_rate`, `bounce_rate`, `unsubscribe_rate`, and `lead_magnet_conversion_rate`.
- Reports MUST be segmentable by persona, campaign, and channel.

#### 3.18 Compliance / Risk Control Layer
- The system MUST enforce data privacy and compliance.
- It MUST manage suppression lists (unsubscribes, bounces) globally.
- It MUST log all actions (audit logs) and mitigate AI hallucination risks via confidence thresholds.

### 4. Non-Functional Requirements
- **Reliability:** The system must gracefully handle scraper blocking and IP bans by pausing operations and notifying administrators.
- **Security:** API keys for AI providers, AdsPower, and Mail servers must be encrypted.
- **Maintainability:** The architecture must be modular so that scraping logic, AI models, and CRM integrations can be updated independently.
