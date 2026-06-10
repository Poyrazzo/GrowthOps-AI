from django.utils import timezone
from crm.models import Lead, Message, EmailAccount
from outreach.smtp import SMTPSender
from ai_engine.email_generator import generate_followup_draft

def dispatch_pending_emails() -> int:
    pending_messages = Message.objects.filter(status='pending')
    count = 0
    for msg in pending_messages:
        if not msg.sender_account:
            account = EmailAccount.objects.filter(is_active=True).first()
            if not account:
                continue
            msg.sender_account = account
            msg.save()
            
        sender = SMTPSender(msg)
        if sender.send():
            if msg.lead.status == 'uncontacted':
                msg.lead.status = 'in_sequence'
                msg.lead.save()
            count += 1
    return count

def process_followups() -> int:
    leads = Lead.objects.filter(status='in_sequence')
    count = 0
    now = timezone.now()
    
    for lead in leads:
        messages = Message.objects.filter(lead=lead).order_by('created_at')
        if not messages.exists():
            continue
            
        latest_msg = messages.last()
        
        # Check if latest msg is sent and > 3 days old
        if latest_msg.status == 'sent' and latest_msg.sent_at and (now - latest_msg.sent_at).days >= 3:
            if messages.count() >= 3:
                continue
                
            # Draft followup
            previous_emails = "\n\n---\n\n".join([m.body for m in messages])
            
            draft_data = generate_followup_draft(
                lead_name=lead.first_name,
                company_name=lead.company.name if lead.company else "",
                previous_emails=previous_emails,
                message_angle=lead.recommended_message_angle
            )
            
            if draft_data and draft_data.get('subject') and draft_data.get('body'):
                Message.objects.create(
                    lead=lead,
                    campaign=lead.campaign,
                    channel='email',
                    subject=draft_data['subject'],
                    body=draft_data['body'],
                    status='pending'
                )
                count += 1
                
    return count
