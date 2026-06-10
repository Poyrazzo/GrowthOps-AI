import requests
import logging

logger = logging.getLogger(__name__)

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
