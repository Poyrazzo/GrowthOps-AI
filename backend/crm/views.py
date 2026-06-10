from rest_framework import viewsets
from .models import (
    Campaign, LeadSource, Company, Lead, EmailAccount, LeadMagnet, Message, Reply,
    SuppressionList, ApprovalQueue, LinkedInTask, AuditLog
)
from .serializers import (
    CampaignSerializer, LeadSourceSerializer, CompanySerializer, LeadSerializer,
    EmailAccountSerializer, LeadMagnetSerializer, MessageSerializer, ReplySerializer,
    SuppressionListSerializer, ApprovalQueueSerializer, LinkedInTaskSerializer, AuditLogSerializer
)

class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.all().order_by('-created_at')
    serializer_class = CampaignSerializer

class LeadSourceViewSet(viewsets.ModelViewSet):
    queryset = LeadSource.objects.all().order_by('-created_at')
    serializer_class = LeadSourceSerializer

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
                Message.objects.filter(id=instance.item_id).update(status='failed')

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
            # Transition the Lead pipeline state if uncontacted
            if instance.lead.status == 'uncontacted':
                instance.lead.status = 'in_sequence'
                instance.lead.save()

class AuditLogViewSet(viewsets.ModelViewSet):
    queryset = AuditLog.objects.all().order_by('-created_at')
    serializer_class = AuditLogSerializer
