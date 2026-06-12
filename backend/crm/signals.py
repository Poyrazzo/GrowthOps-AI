from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from crm.models import Campaign


@receiver(pre_save, sender=Campaign)
def _stash_old_status(sender, instance, **kwargs):
    """Remember the previous status so post_save can detect a real transition."""
    if instance.pk:
        old = Campaign.objects.filter(pk=instance.pk).values_list('status', flat=True).first()
        instance._old_status = old
    else:
        instance._old_status = None


@receiver(post_save, sender=Campaign)
def trigger_scrape_on_activation(sender, instance, created, **kwargs):
    """When a campaign transitions into 'active', immediately scrape its sources
    instead of waiting for the next 6h beat tick. Routing mirrors
    trigger_scheduled_scrapes_task: dynamic -> playwright queue, linkedin -> never."""
    old_status = getattr(instance, '_old_status', None)
    became_active = instance.status == 'active' and old_status != 'active'
    if not became_active:
        return

    from crm.tasks import run_static_scrape, run_dynamic_scrape
    from django.utils import timezone

    sources = instance.sources.exclude(source_type='linkedin')
    for source in sources:
        source.last_scraped_at = timezone.now()
        source.save(update_fields=['last_scraped_at'])
        if source.source_type == 'dynamic':
            run_dynamic_scrape.delay(source.url, campaign_id=str(instance.id), source_id=str(source.id))
        else:
            run_static_scrape.delay(source.url, campaign_id=str(instance.id), source_id=str(source.id))
