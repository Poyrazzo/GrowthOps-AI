import logging
import os
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import (
    Campaign, LeadSource, Company, Lead, EmailAccount, LeadMagnet, Message, Reply,
    SuppressionList, ApprovalQueue, LinkedInTask, AuditLog, Activity, LeadMagnetSubmission
)
from .serializers import (
    CampaignSerializer, LeadSourceSerializer, CompanySerializer, LeadSerializer,
    EmailAccountSerializer, LeadMagnetSerializer, MessageSerializer, ReplySerializer,
    SuppressionListSerializer, ApprovalQueueSerializer, LinkedInTaskSerializer, AuditLogSerializer,
    ActivitySerializer, LeadMagnetSubmissionSerializer
)
from .utils import log_activity

logger = logging.getLogger(__name__)

class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.all().order_by('-created_at')
    serializer_class = CampaignSerializer

    @action(detail=True, methods=['post'])
    def scrape_now(self, request, pk=None):
        """Run the campaign immediately: scrape every non-LinkedIn source right now,
        bypassing the 6h beat schedule and the 24h per-source cooldown. Safe to call
        repeatedly — it just (re)scrapes and adds any new leads found."""
        campaign = self.get_object()
        if campaign.status != 'active':
            return Response(
                {"detail": "Campaign must be active to run. Activate it first."},
                status=400
            )

        from .tasks import run_static_scrape, run_dynamic_scrape
        sources = campaign.sources.exclude(source_type='linkedin')
        if not sources.exists():
            return Response(
                {"detail": "No scrapeable sources. Add sources to this campaign first."},
                status=400
            )

        triggered = 0
        for source in sources:
            source.last_scraped_at = timezone.now()
            source.save(update_fields=['last_scraped_at'])
            if source.source_type == 'dynamic':
                run_dynamic_scrape.delay(source.url, campaign_id=str(campaign.id), source_id=str(source.id))
            else:
                run_static_scrape.delay(source.url, campaign_id=str(campaign.id), source_id=str(source.id))
            triggered += 1

        return Response({
            "detail": f"Running now — scraping {triggered} source(s). Watch the Activity Monitor for results."
        }, status=202)

    @action(detail=True, methods=['post'])
    def restart(self, request, pk=None):
        """Fresh restart: cancel open drafts and their approval entries, reset
        in-sequence leads to uncontacted, clear scrape cooldowns, then reactivate.
        Reactivation fires the signal that immediately re-scrapes all sources."""
        campaign = self.get_object()

        open_messages = Message.objects.filter(
            campaign=campaign, status__in=['needs_review', 'pending']
        )
        open_ids = [str(m.id) for m in open_messages]
        cancelled = open_messages.update(status='cancelled')
        if open_ids:
            ApprovalQueue.objects.filter(
                item_type='message_draft', item_id__in=open_ids, status='pending'
            ).update(status='rejected')

        reset = Lead.objects.filter(
            campaign=campaign, status='in_sequence'
        ).update(status='uncontacted')

        # Clear cooldowns so the activation signal re-scrapes everything now
        campaign.sources.update(last_scraped_at=None)

        # Force a draft->active transition so the activation signal always fires
        Campaign.objects.filter(pk=campaign.pk).update(status='draft')
        campaign.refresh_from_db()
        campaign.status = 'active'
        campaign.save()

        # Existing uncontacted leads won't be re-scraped into existence, so
        # queue drafting for any that still lack a live draft.
        from .tasks import generate_draft_task
        uncontacted = Lead.objects.filter(campaign=campaign, status='uncontacted')
        for lead in uncontacted:
            generate_draft_task.delay(str(lead.id))

        AuditLog.objects.create(
            action="Campaign Restarted",
            resource_type="Campaign",
            resource_id=str(campaign.id),
            details={"cancelled_drafts": cancelled, "leads_reset": reset,
                     "leads_requeued": uncontacted.count()}
        )

        return Response({
            "detail": (f"Campaign restarted: {cancelled} open drafts cancelled, "
                       f"{reset} leads reset, sources re-scraping, "
                       f"{uncontacted.count()} leads queued for drafting."),
            "status": "active"
        }, status=200)

class LeadSourceViewSet(viewsets.ModelViewSet):
    queryset = LeadSource.objects.all().order_by('-created_at')
    serializer_class = LeadSourceSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        campaign = self.request.query_params.get('campaign')
        if campaign:
            qs = qs.filter(campaign_id=campaign)
        return qs

    @action(detail=True, methods=['post'])
    def scrape(self, request, pk=None):
        """Manually triggers a scrape of this source (the scheduled beat task covers
        active campaigns automatically). LinkedIn sources are never bot-scraped."""
        source = self.get_object()
        if source.source_type == 'linkedin':
            return Response(
                {"detail": "LinkedIn sources are human-in-the-loop only and cannot be auto-scraped."},
                status=400
            )

        from .tasks import run_static_scrape, run_dynamic_scrape
        campaign_id = str(source.campaign_id) if source.campaign_id else None
        if source.source_type == 'dynamic':
            task = run_dynamic_scrape.delay(source.url, campaign_id=campaign_id, source_id=str(source.id))
        else:
            task = run_static_scrape.delay(source.url, campaign_id=campaign_id, source_id=str(source.id))

        return Response({"detail": "Scrape queued.", "task_id": task.id}, status=202)

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all().order_by('-created_at')
    serializer_class = CompanySerializer

class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.all().order_by('-created_at')
    serializer_class = LeadSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        campaign = self.request.query_params.get('campaign')
        if campaign:
            qs = qs.filter(campaign_id=campaign)
        return qs

    def perform_destroy(self, instance):
        # Deleting a lead must not leave orphaned approval entries pointing at
        # its (cascade-deleted) messages -> the queue would render broken cards.
        msg_ids = [str(m) for m in instance.messages.values_list('id', flat=True)]
        if msg_ids:
            ApprovalQueue.objects.filter(item_type='message_draft', item_id__in=msg_ids).delete()
        instance.delete()

    @action(detail=True, methods=['post'])
    def draft(self, request, pk=None):
        """Operator action: queue AI drafting for this lead right now."""
        lead = self.get_object()
        if not lead.campaign:
            return Response({"detail": "Lead has no campaign — assign one first."}, status=400)
        if lead.campaign.outreach_channel == 'linkedin':
            from .tasks import generate_linkedin_task_task
            generate_linkedin_task_task.delay(str(lead.id))
        else:
            if not lead.email:
                return Response({"detail": "Lead has no email address."}, status=400)
            from .tasks import generate_draft_task
            generate_draft_task.delay(str(lead.id))
        return Response({"detail": "Drafting queued. The draft will appear in the Approval Queue shortly."}, status=202)

    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        """Delete many leads at once. Body: {"ids": [...]} or {"campaign": "<id>"}."""
        ids = request.data.get('ids')
        campaign_id = request.data.get('campaign')

        if ids:
            qs = Lead.objects.filter(id__in=ids)
        elif campaign_id:
            qs = Lead.objects.filter(campaign_id=campaign_id)
        else:
            return Response({"detail": "Provide 'ids' or 'campaign'."}, status=400)

        msg_ids = [str(m) for m in Message.objects.filter(lead__in=qs).values_list('id', flat=True)]
        if msg_ids:
            ApprovalQueue.objects.filter(item_type='message_draft', item_id__in=msg_ids).delete()

        count = qs.count()
        qs.delete()
        return Response({"detail": f"Deleted {count} leads."}, status=200)

class EmailAccountViewSet(viewsets.ModelViewSet):
    queryset = EmailAccount.objects.all().order_by('-created_at')
    serializer_class = EmailAccountSerializer

class LeadMagnetViewSet(viewsets.ModelViewSet):
    queryset = LeadMagnet.objects.all().order_by('-created_at')
    serializer_class = LeadMagnetSerializer

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all().order_by('-created_at')
    serializer_class = MessageSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        campaign = self.request.query_params.get('campaign')
        if campaign:
            qs = qs.filter(campaign_id=campaign)
        return qs

class ReplyViewSet(viewsets.ModelViewSet):
    queryset = Reply.objects.all().order_by('-created_at')
    serializer_class = ReplySerializer

class SuppressionListViewSet(viewsets.ModelViewSet):
    queryset = SuppressionList.objects.all().order_by('-created_at')
    serializer_class = SuppressionListSerializer

class ApprovalQueueViewSet(viewsets.ModelViewSet):
    queryset = ApprovalQueue.objects.all().order_by('-created_at')
    serializer_class = ApprovalQueueSerializer

    def perform_update(self, serializer):
        instance = serializer.save()
        if instance.status == 'approved':
            AuditLog.objects.create(
                action="Human Review: Approved",
                resource_type="ApprovalQueue",
                resource_id=str(instance.id),
                details={"item_type": instance.item_type, "reason": instance.reason_for_review}
            )
            if instance.item_type == 'message_draft':
                Message.objects.filter(id=instance.item_id).update(status='pending')
        elif instance.status == 'rejected':
            AuditLog.objects.create(
                action="Human Review: Rejected",
                resource_type="ApprovalQueue",
                resource_id=str(instance.id),
                details={"item_type": instance.item_type, "reason": instance.reason_for_review}
            )
            if instance.item_type == 'message_draft':
                Message.objects.filter(id=instance.item_id).update(status='cancelled')

class LinkedInTaskViewSet(viewsets.ModelViewSet):
    queryset = LinkedInTask.objects.all().order_by('-created_at')
    serializer_class = LinkedInTaskSerializer

    def perform_update(self, serializer):
        instance = serializer.save()
        if instance.status == 'completed':
            # Log the manual action
            AuditLog.objects.create(
                action="LinkedIn Manual Task Completed",
                resource_type="LinkedInTask",
                resource_id=str(instance.id),
                details={"task_type": instance.task_type}
            )
            log_activity(instance.lead, 'linkedin_task_completed',
                         f"Operator completed '{instance.task_type}' task", campaign=instance.campaign)
            # Transition the Lead pipeline state if uncontacted
            if instance.lead.status == 'uncontacted':
                instance.lead.status = 'in_sequence'
                instance.lead.save()
            # SRS 3.14 funnel: an accepted connection chains into an AI-drafted DM task
            if instance.task_type == 'connect':
                try:
                    from .tasks import generate_linkedin_dm_task
                    generate_linkedin_dm_task.delay(str(instance.lead_id))
                except Exception as e:
                    logger.error(f"Could not queue DM draft task: {e}")

class AuditLogViewSet(viewsets.ModelViewSet):
    queryset = AuditLog.objects.all().order_by('-created_at')
    serializer_class = AuditLogSerializer

class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Activity.objects.all().order_by('-created_at')
    serializer_class = ActivitySerializer

    def get_queryset(self):
        qs = super().get_queryset()
        campaign = self.request.query_params.get('campaign')
        if campaign:
            qs = qs.filter(campaign_id=campaign)
        return qs[:50]

class LeadMagnetSubmissionViewSet(viewsets.ModelViewSet):
    """Records lead-magnet form submissions (SRS 3.8): matches/creates the lead,
    logs the activity, and notifies the team via the n8n webhook."""
    queryset = LeadMagnetSubmission.objects.all().order_by('-created_at')
    serializer_class = LeadMagnetSubmissionSerializer

    def perform_create(self, serializer):
        submission = serializer.save()

        lead = Lead.objects.filter(email__iexact=submission.email).first()
        if not lead:
            lead = Lead.objects.create(email=submission.email.lower(), status='uncontacted')
        submission.lead = lead
        submission.save(update_fields=['lead'])

        log_activity(lead, 'lead_magnet_submitted',
                     f"Submitted form for '{submission.lead_magnet.name}'",
                     {"form_data": submission.form_data})

        from .utils import send_notification_webhook
        send_notification_webhook(
            event_type="lead_magnet_submission",
            payload={
                "lead_email": submission.email,
                "lead_magnet": submission.lead_magnet.name,
            }
        )


@require_GET
def logs_view(request):
    """Returns the last N lines of the system log file.

    Query params:
      lines  — how many tail lines to return (default 200, max 2000)
      filter — optional substring filter applied per line
    """
    log_path = Path(settings.BASE_DIR) / 'logs' / 'growthops.log'
    n = min(int(request.GET.get('lines', 200)), 2000)
    substring = request.GET.get('filter', '').lower()

    if not log_path.exists():
        return JsonResponse({'lines': [], 'note': 'Log file not created yet. Run a scrape first.'})

    with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
        all_lines = f.readlines()

    if substring:
        all_lines = [l for l in all_lines if substring in l.lower()]

    tail = [l.rstrip('\n') for l in all_lines[-n:]]
    return JsonResponse({'lines': tail, 'total': len(all_lines)})
