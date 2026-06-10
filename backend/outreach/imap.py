import re
import imaplib
import email
from email.utils import parseaddr
from django.utils import timezone
from crm.models import EmailAccount, Lead, Message, Reply, AuditLog
from crm.utils import log_activity
from core.encryption import decrypt

EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

# Senders that indicate a delivery-status notification rather than a human reply
BOUNCE_SENDER_MARKERS = ('mailer-daemon', 'postmaster', 'mail delivery', 'maildelivery')

class IMAPReader:
    def __init__(self, account: EmailAccount):
        self.account = account

    def _get_plain_text(self, email_message):
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        return part.get_payload(decode=True).decode(errors='replace')
                    except Exception:
                        pass
        else:
            if email_message.get_content_type() == "text/plain":
                try:
                    return email_message.get_payload(decode=True).decode(errors='replace')
                except Exception:
                    pass
        return "Could not extract plain text"

    def _match_by_thread(self, msg) -> Message:
        """Primary matching: In-Reply-To / References headers against our Message-IDs."""
        in_reply_to = msg.get("In-Reply-To")
        references = msg.get("References")

        candidate_ids = []
        if in_reply_to:
            candidate_ids.append(in_reply_to.strip())
        if references:
            candidate_ids.extend(ref.strip() for ref in references.split())

        for target_id in candidate_ids:
            original = Message.objects.filter(message_id=target_id).first()
            if original:
                return original
        return None

    def _match_by_sender(self, from_addr: str) -> Message:
        """Fallback matching (SRS 3.12): the sender's address against known leads."""
        if not from_addr:
            return None
        lead = Lead.objects.filter(email__iexact=from_addr).first()
        if not lead:
            return None
        return Message.objects.filter(lead=lead, channel='email', status='sent').order_by('-sent_at').first()

    def _match_bounce(self, body_text: str) -> Message:
        """NDR matching: bounce reports rarely thread, so scan the report body for
        a recipient address belonging to one of our leads."""
        if not body_text:
            return None
        for found_email in set(re.findall(EMAIL_REGEX, body_text)):
            if found_email.lower() == self.account.email.lower():
                continue
            lead = Lead.objects.filter(email__iexact=found_email).first()
            if lead:
                return Message.objects.filter(lead=lead, channel='email', status='sent').order_by('-sent_at').first()
        return None

    def read_inbox(self) -> int:
        if not self.account.imap_host:
            self._log_audit("Failed", "No IMAP host configured")
            return 0

        try:
            password = decrypt(self.account.password_encrypted)

            if self.account.imap_use_ssl:
                mail = imaplib.IMAP4_SSL(self.account.imap_host, self.account.imap_port or 993)
            else:
                mail = imaplib.IMAP4(self.account.imap_host, self.account.imap_port or 143)
            login_user = self.account.username or self.account.email
            mail.login(login_user, password)

            mail.select("inbox")

            status, messages = mail.search(None, "UNSEEN")
            if status != "OK" or not messages[0]:
                mail.logout()
                return 0

            email_ids = messages[0].split()
            replies_created = 0

            for eid in email_ids:
                # PEEK so a crash mid-processing doesn't permanently lose unread mail;
                # we flag \Seen explicitly once the message has been handled.
                res, msg_data = mail.fetch(eid, "(BODY.PEEK[])")
                if res != "OK":
                    continue

                for response_part in msg_data:
                    if not isinstance(response_part, tuple):
                        continue
                    msg = email.message_from_bytes(response_part[1])

                    from_name, from_addr = parseaddr(msg.get("From", ""))
                    from_addr = (from_addr or '').lower()
                    subject = (msg.get("Subject") or '').lower()
                    body_text = self._get_plain_text(msg)

                    is_bounce_notification = (
                        any(marker in from_addr for marker in BOUNCE_SENDER_MARKERS)
                        or any(marker in from_name.lower() for marker in BOUNCE_SENDER_MARKERS)
                        or 'undeliver' in subject or 'delivery status' in subject
                    )

                    original_msg = self._match_by_thread(msg)
                    if not original_msg and is_bounce_notification:
                        original_msg = self._match_bounce(body_text)
                    if not original_msg and not is_bounce_notification:
                        original_msg = self._match_by_sender(from_addr)

                    if not original_msg:
                        # Unrelated mail: mark seen so we don't reprocess it every poll
                        mail.store(eid, '+FLAGS', '\\Seen')
                        continue

                    reply_record = Reply.objects.create(
                        lead=original_msg.lead,
                        message=original_msg,
                        body=body_text,
                        received_at=timezone.now()
                    )
                    replies_created += 1
                    log_activity(original_msg.lead, 'reply_received', f"From {from_addr or 'unknown'}")

                    # Only a genuine human reply is a hard stop-condition here. Bounce
                    # notifications must NOT mark the lead as 'replied'; the AI
                    # classifier transitions those to disqualified + suppression.
                    if not is_bounce_notification and original_msg.lead.status != 'replied':
                        original_msg.lead.status = 'replied'
                        original_msg.lead.save()

                    # Trigger AI classification task (a broker outage must not abort the read loop)
                    try:
                        from crm.tasks import classify_reply_task
                        classify_reply_task.delay(str(reply_record.id))
                    except Exception as e:
                        self._log_audit("Warning", f"Could not queue classification for reply {reply_record.id}: {e}")

                    mail.store(eid, '+FLAGS', '\\Seen')

            mail.logout()

            if replies_created > 0:
                self._log_audit("Success", f"Processed {replies_created} replies")

            return replies_created

        except Exception as e:
            self._log_audit("Failed", f"IMAP Error: {str(e)}")
            return 0

    def _log_audit(self, action: str, details: str):
        AuditLog.objects.create(
            action=f"IMAP Reader: {action}",
            resource_type="EmailAccount",
            resource_id=str(self.account.id),
            details={"info": details}
        )
