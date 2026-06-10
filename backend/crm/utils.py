import requests
import logging

logger = logging.getLogger(__name__)

# Free mailbox providers: an email on these domains tells us nothing about the
# lead's employer, so we never create a Company from them.
FREE_EMAIL_PROVIDERS = {
    'gmail.com', 'googlemail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
    'live.com', 'icloud.com', 'me.com', 'aol.com', 'protonmail.com', 'proton.me',
    'mail.com', 'gmx.com', 'gmx.net', 'yandex.com', 'yandex.ru', 'zoho.com',
}

def log_activity(lead, activity_type: str, description: str = "", metadata: dict = None, campaign=None):
    """Records a CRM Activity for a lead (SRS 3.9 'activities' entity)."""
    from crm.models import Activity
    try:
        Activity.objects.create(
            lead=lead,
            campaign=campaign or lead.campaign,
            activity_type=activity_type,
            description=description,
            metadata=metadata or {}
        )
    except Exception as e:
        logger.error(f"Failed to log activity {activity_type} for lead {lead.id}: {e}")

# The n8n container is accessible on the Docker network as 'n8n:5678'
# This webhook URL should map to the Webhook Node in your n8n workflow.
N8N_WEBHOOK_URL = "http://n8n:5678/webhook/growthops-events"

def send_notification_webhook(event_type: str, payload: dict):
    """
    Sends an event payload to the n8n webhook listener for external notifications.
    """
    data = {
        "event_type": event_type,
        "payload": payload
    }
    
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=data, timeout=5)
        response.raise_for_status()
        logger.info(f"Successfully pushed {event_type} event to n8n.")
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to push event to n8n webhook: {str(e)}")
        return False
