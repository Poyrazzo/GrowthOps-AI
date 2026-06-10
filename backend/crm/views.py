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

class LinkedInTaskViewSet(viewsets.ModelViewSet):
    queryset = LinkedInTask.objects.all().order_by('-created_at')
    serializer_class = LinkedInTaskSerializer

class AuditLogViewSet(viewsets.ModelViewSet):
    queryset = AuditLog.objects.all().order_by('-created_at')
    serializer_class = AuditLogSerializer
