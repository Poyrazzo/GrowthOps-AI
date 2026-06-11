from django.db.models.signals import post_save
from django.dispatch import receiver
from crm.models import Campaign, LeadSource
from crm.tasks import run_dynamic_scrape


@receiver(post_save, sender=Campaign)
def trigger_scrape_on_activation(sender, instance, created, update_fields, **kwargs):
    """Immediately scrape all sources when campaign is activated."""

    # Check if status was changed to 'active'
    if update_fields is None or 'status' not in update_fields:
        return

    if instance.status == 'active':
        sources = LeadSource.objects.filter(campaign=instance)

        for source in sources:
            # Queue immediate scrape task
            run_dynamic_scrape.apply_async(
                args=[source.url, str(instance.id), None, None, str(source.id)],
                queue='default'
            )
