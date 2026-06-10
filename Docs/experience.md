# Experience Log

This document serves as our project diary and knowledge base.

**Rule:** We will write everything we thought, developed, implemented, bugs we encountered and fixed, and everything else we experienced while building the Growth Automation & AI Ops System inside this document.

## Implementation of Phase 5 (Step 5.1)
- **Security Dependency:** Installed the `cryptography` Python package to handle sensitive email credentials.
- **Fernet Encryption Utility:** Created `backend/core/encryption.py` which dynamically generates a 32-byte URL-safe base64 key by hashing the Django `SECRET_KEY`. This provides a stable, symmetrical encryption algorithm that securely hides SMTP passwords in the database without needing complex key-vault setups for the MVP.
- **Model Override Magic:** Overrode the `.save()` method on the `EmailAccount` model. If a user inputs a raw password into the Django Admin interface, the model automatically detects it (by verifying it lacks the `gAAAAAB` Fernet signature), encrypts it, and saves the ciphertext to PostgreSQL seamlessly.
- **SMTP Engine:** Built `backend/outreach/smtp.py` housing the `SMTPSender` class.
- **Dynamic Email Dispatch:** The sender decrypts the credentials and dynamically instantiates Django's `EmailBackend`, bypassing Django's global `EMAIL_HOST` settings. This allows the system to send emails from hundreds of different worker accounts simultaneously.
- **Suppression & Auditing:** The class aggressively queries the `SuppressionList` table to prevent sending emails to bounded/unsubscribed contacts. It also pushes native logs to the `AuditLog` table on success or failure.
- **Thread Tracking Prep:** The utility explicitly injects a `Message-ID: <{message.id}@growthops.ai>` header into every outgoing email. This is a critical architectural decision for Step 5.2, as it guarantees that when a prospect replies, their email client will include this exact ID in the `In-Reply-To` header, allowing the system to instantly map the reply back to the correct `Message` and `Lead` in our database.
- **Verification:** Rebuilt the Docker containers and successfully tested the encryption logic and class initialization in the Django shell.
