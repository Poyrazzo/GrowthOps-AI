# Experience Log

This document serves as our project diary and knowledge base.

**Rule:** We will write everything we thought, developed, implemented, bugs we encountered and fixed, and everything else we experienced while building the Growth Automation & AI Ops System inside this document.

## Implementation of Phase 5 (Step 5.1, 5.2, 5.3, & 5.4)
- **Security Dependency:** Installed the `cryptography` Python package to handle sensitive email credentials.
- **SMTP Engine:** Built `backend/outreach/smtp.py` housing the `SMTPSender` class.
- **IMAP Reader:** Built `backend/outreach/imap.py` housing the `IMAPReader` class. Logs in securely, fetches `UNSEEN` emails, matches `In-Reply-To` headers, and creates a `Reply` database record.
- **Background Orchestration:** Integrated `poll_all_inboxes_task` into Celery Beat with a 5-minute recurring schedule.
- **AI Reply Classifier:** Built `backend/ai_engine/reply_classifier.py`. Uses LangChain and Pydantic to strictly coerce the OpenAI model (`gpt-4o-mini`) into outputting exact schema categories for an incoming prospect reply.
- **Autonomous Feedback Loop:** Added `classify_reply_task` to `backend/crm/tasks.py` and chained it directly into `imap.py`. Guardrails automatically add to `SuppressionList` upon bounces/unsubscribes.
- **Outreach Sequence Manager:** Built `backend/outreach/sequence.py` to fill the crucial gap of dispatching drafted emails. 
- **Dispatcher Task:** Created `dispatch_pending_emails` which runs every 10 minutes, picks up any AI drafts with a `pending` status, assigns an active Email Account, and sends them over SMTP.
- **Follow-up AI Drafter:** Appended `generate_followup_draft` to `backend/ai_engine/email_generator.py`. This prompt explicitly reads the *entire thread history* of previous emails sent to a specific lead and drafts a polite "bump" without repeating the original pitch.
- **Sequence Orchestrator:** Created `process_followups_task` which runs every hour. It scans the CRM for all leads `in_sequence`, calculates the timedelta since their last sent email, and if `> 3 days` have elapsed, it automatically triggers the AI to write a follow-up. It implements a strict stop-condition: a sequence naturally halts once 3 total emails have been dispatched.
