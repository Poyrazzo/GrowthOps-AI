# Experience Log

This document serves as our project diary and knowledge base.

**Rule:** We will write everything we thought, developed, implemented, bugs we encountered and fixed, and everything else we experienced while building the Growth Automation & AI Ops System inside this document.

## Implementation of Phase 5
- **Security Dependency:** Installed the `cryptography` Python package to handle sensitive email credentials.
- **SMTP Engine:** Built `backend/outreach/smtp.py` housing the `SMTPSender` class. Upgraded it with a strict `daily_limit` throttle check to protect domain reputation.
- **IMAP Reader:** Built `backend/outreach/imap.py` housing the `IMAPReader` class. Logs in securely, fetches `UNSEEN` emails, matches `In-Reply-To` headers, and creates a `Reply` database record.
- **Background Orchestration:** Integrated `poll_all_inboxes_task` into Celery Beat.
- **AI Reply Classifier:** Built `backend/ai_engine/reply_classifier.py`. Guardrails automatically add to `SuppressionList` upon bounces/unsubscribes.
- **Outreach Sequence Manager:** Built `backend/outreach/sequence.py` to fill the crucial gap of dispatching drafted emails.
- **Load-Balancing Algorithm:** We encountered a critical bottleneck where all emails would send from a single account until failure. I engineered a `get_account_with_capacity()` helper function that calculates exactly how many emails each active account has sent today, and routes new drafts to the account with the most remaining capacity.
- **Identity Preservation Fix:** Discovered a flaw where follow-up sequences would pick a random active sender account, breaking thread continuity. Patched `process_followups` to strictly inherit `latest_msg.sender_account` to ensure follow-ups come from the identical sender.
- **Verification:** Ran python syntactical evaluations and re-warmed the Celery beat and worker nodes to digest the newly hardened architecture. Phase 5 is fully production ready.
