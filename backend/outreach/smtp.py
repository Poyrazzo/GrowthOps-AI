from django.core.mail import EmailMessage
from django.core.mail.backends.smtp import EmailBackend
from django.utils import timezone
from crm.models import Message, SuppressionList, AuditLog
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
            self._log_audit("Failed", "Lead has no email address")
            return False
            
        # Check suppression list
        if SuppressionList.objects.filter(email=self.message.lead.email).exists():
            self.message.status = 'bounced' # Treat suppressed as bounced/failed
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
                use_tls=True,
                fail_silently=False,
            )
            
            custom_msg_id = f"<{self.message.id}@growthops.ai>"
            
            email = EmailMessage(
                subject=self.message.subject,
                body=self.message.body,
                from_email=self.account.email,
                to=[self.message.lead.email],
                connection=backend,
            )
            email.extra_headers = {'Message-ID': custom_msg_id}
            
            email.send()
            
            self.message.status = 'sent'
            self.message.message_id = custom_msg_id
            self.message.sent_at = timezone.now()
            self.message.save()
            
            self._log_audit("Sent", f"Successfully sent to {self.message.lead.email}")
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
