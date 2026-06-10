import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

from celery.schedules import crontab

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

app.conf.beat_schedule = {
    'poll-inboxes-every-5-minutes': {
        'task': 'crm.tasks.poll_all_inboxes_task',
        'schedule': crontab(minute='*/5'),
    },
    'dispatch-emails-every-10-minutes': {
        'task': 'crm.tasks.dispatch_emails_task',
        'schedule': crontab(minute='*/10'),
    },
    'process-followups-every-hour': {
        'task': 'crm.tasks.process_followups_task',
        'schedule': crontab(minute='0'),
    },
}
