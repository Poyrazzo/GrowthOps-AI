import imaplib
import email
from email.header import decode_header
from django.utils import timezone
from crm.models import EmailAccount, Message, Reply, AuditLog
from core.encryption import decrypt

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
                        return part.get_payload(decode=True).decode()
                    except Exception:
                        pass
        else:
            if email_message.get_content_type() == "text/plain":
                try:
                    return email_message.get_payload(decode=True).decode()
                except Exception:
                    pass
        return "Could not extract plain text"

    def read_inbox(self) -> int:
        if not self.account.imap_host:
            self._log_audit("Failed", "No IMAP host configured")
            return 0
            
        try:
            password = decrypt(self.account.password_encrypted)
            
            mail = imaplib.IMAP4_SSL(self.account.imap_host, self.account.imap_port or 993)
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
                res, msg_data = mail.fetch(eid, "(RFC822)")
                if res != "OK":
                    continue
                    
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        in_reply_to = msg.get("In-Reply-To")
                        references = msg.get("References")
                        
                        # Clean up headers
                        target_id = None
                        if in_reply_to:
                            target_id = in_reply_to.strip()
                        elif references:
                            target_id = references.split()[0].strip()
                            
                        if not target_id:
                            continue
                            
                        # Find original message
                        original_msg = Message.objects.filter(message_id=target_id).first()
                        if not original_msg:
                            continue
                            
                        # Extract body
                        body_text = self._get_plain_text(msg)
                        
                        # Create reply
                        reply_record = Reply.objects.create(
                            lead=original_msg.lead,
                            message=original_msg,
                            body=body_text,
                            received_at=timezone.now()
                        )
                        replies_created += 1
                        
                        # Mark lead status as replied if it wasn't
                        if original_msg.lead.status != 'replied':
                            original_msg.lead.status = 'replied'
                            original_msg.lead.save()
                            
                        # Trigger AI classification task
                        from crm.tasks import classify_reply_task
                        classify_reply_task.delay(str(reply_record.id))
                            
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
