from django.core.mail import EmailMessage
from django.core.mail.backends.smtp import EmailBackend
from django.db.models import Q
from django.utils import timezone
from crm.models import Message, SuppressionList, AuditLog
from crm.utils import log_activity
from core.encryption import decrypt

class SMTPSender:
    def __init__(self, message: Message):
        self.message = message
        self.account = message.sender_account

    def send(self) -> bool:
        if not self.account:
            self._log_audit("Failed", "No sender account configured")
            return False

        if not self.message.lead or not self.message.lead.email:
            self.message.status = 'failed'
            self.message.save()
            self._log_audit("Failed", "Lead has no email address")
            return False

        # Check daily limit: DEFER (keep pending for a later dispatch run), don't kill the message
        sent_today = Message.objects.filter(sender_account=self.account, status='sent', sent_at__date=timezone.now().date()).count()
        if sent_today >= self.account.daily_limit:
            self._log_audit("Deferred", "Daily limit reached for this account; message stays pending")
            return False

        # Check suppression list (by exact email AND by blocked domain)
        recipient = self.message.lead.email
        recipient_domain = recipient.split('@', 1)[1] if '@' in recipient else ''
        if SuppressionList.objects.filter(Q(email=recipient) | Q(domain=recipient_domain, domain__gt='')).exists():
            self.message.status = 'bounced'  # Treat suppressed as bounced/failed
            self.message.save()
            self._log_audit("Blocked", "Lead is on the suppression list")
            return False

        try:
            password = decrypt(self.account.password_encrypted)

            backend = EmailBackend(
                host=self.account.smtp_host,
                port=self.account.smtp_port,
                username=self.account.username,
                password=password,
                use_tls=(self.account.smtp_encryption == 'tls'),
                use_ssl=(self.account.smtp_encryption == 'ssl'),
                fail_silently=False,
            )

            custom_msg_id = f"<{self.message.id}@growthops.ai>"

            headers = {'Message-ID': custom_msg_id}

            # Thread follow-ups into the original conversation: reference the most
            # recent email we already sent this lead so clients render one thread.
            previous = Message.objects.filter(
                lead=self.message.lead, channel='email', status='sent'
            ).exclude(id=self.message.id).exclude(message_id__isnull=True).order_by('-sent_at').first()
            if previous and previous.message_id:
                headers['In-Reply-To'] = previous.message_id
                headers['References'] = previous.message_id

            email = EmailMessage(
                subject=self.message.subject,
                body=self.message.body,
                from_email=self.account.email,
                to=[recipient],
                connection=backend,
                headers=headers,
            )

            email.send()

            self.message.status = 'sent'
            self.message.message_id = custom_msg_id
            self.message.sent_at = timezone.now()
            self.message.save()

            self._log_audit("Sent", f"Successfully sent to {recipient}")
            log_activity(self.message.lead, 'email_sent', f"Sent: {self.message.subject}", campaign=self.message.campaign)
            return True

        except Exception as e:
            self.message.status = 'failed'
            self.message.save()
            self._log_audit("Failed", f"SMTP Error: {str(e)}")
            return False

    def _log_audit(self, action: str, details: str):
        AuditLog.objects.create(
            action=f"SMTP Send: {action}",
            resource_type="Message",
            resource_id=str(self.message.id),
            details={"info": details}
        )
