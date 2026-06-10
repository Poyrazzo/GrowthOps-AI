import logging
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

class LeadSourceViewSet(viewsets.ModelViewSet):
    queryset = LeadSource.objects.all().order_by('-created_at')
    serializer_class = LeadSourceSerializer

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

class EmailAccountViewSet(viewsets.ModelViewSet):
    queryset = EmailAccount.objects.all().order_by('-created_at')
    serializer_class = EmailAccountSerializer

class LeadMagnetViewSet(viewsets.ModelViewSet):
    queryset = LeadMagnet.objects.all().order_by('-created_at')
    serializer_class = LeadMagnetSerializer

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all().order_by('-created_at')
    serializer_class = MessageSerializer

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
