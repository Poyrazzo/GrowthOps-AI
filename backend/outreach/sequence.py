from django.utils import timezone
from crm.models import Lead, Message, EmailAccount
from outreach.smtp import SMTPSender
from ai_engine.email_generator import generate_followup_draft

def get_account_with_capacity() -> EmailAccount:
    """Finds the active EmailAccount with the most remaining daily capacity."""
    today = timezone.now().date()
    accounts = EmailAccount.objects.filter(is_active=True)
    best_account = None
    most_capacity = -1
    
    for acc in accounts:
        sent_today = Message.objects.filter(sender_account=acc, status='sent', sent_at__date=today).count()
        capacity = acc.daily_limit - sent_today
        if capacity > most_capacity:
            most_capacity = capacity
            best_account = acc
            
    if most_capacity > 0:
        return best_account
    return None

def dispatch_pending_emails() -> int:
    pending_messages = Message.objects.filter(status='pending')
    count = 0
    today = timezone.now().date()
    
    for msg in pending_messages:
        if not msg.sender_account:
            account = get_account_with_capacity()
            if not account:
                # No system-wide capacity left today
                break
            msg.sender_account = account
            msg.save()
        else:
            # It's a follow-up, check if THIS specific account has capacity
            sent_today = Message.objects.filter(sender_account=msg.sender_account, status='sent', sent_at__date=today).count()
            if sent_today >= msg.sender_account.daily_limit:
                continue
            
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
                status = 'needs_review' if lead.requires_human_review else 'pending'
                
                msg = Message.objects.create(
                    lead=lead,
                    campaign=lead.campaign,
                    sender_account=latest_msg.sender_account, # Identity preservation fix
                    channel='email',
                    subject=draft_data['subject'],
                    body=draft_data['body'],
                    status=status
                )
                
                if status == 'needs_review':
                    from crm.models import ApprovalQueue
                    ApprovalQueue.objects.create(
                        item_type='message_draft',
                        item_id=str(msg.id),
                        status='pending',
                        reason_for_review=f"AI drafted a follow-up email for {lead.email}."
                    )
                
                count += 1
                
    return count
