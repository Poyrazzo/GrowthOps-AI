from rest_framework import serializers
from .models import (
    Campaign, LeadSource, Company, Lead, EmailAccount, LeadMagnet, Message, Reply,
    SuppressionList, ApprovalQueue, LinkedInTask, AuditLog
)

class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = '__all__'

class LeadSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadSource
        fields = '__all__'

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'

class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = '__all__'

class EmailAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailAccount
        fields = '__all__'

class LeadMagnetSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadMagnet
        fields = '__all__'

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'

class ReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = Reply
        fields = '__all__'

class SuppressionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuppressionList
        fields = '__all__'

class ApprovalQueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalQueue
        fields = '__all__'

class LinkedInTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinkedInTask
        fields = '__all__'

class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'
