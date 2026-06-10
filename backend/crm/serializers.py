from django.core.exceptions import ValidationError
from rest_framework import serializers
from .models import (
    Campaign, LeadSource, Company, Lead, EmailAccount, LeadMagnet, Message, Reply,
    SuppressionList, ApprovalQueue, LinkedInTask, AuditLog, Activity, LeadMagnetSubmission
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
        # Never leak mailbox credentials through the API
        extra_kwargs = {'password_encrypted': {'write_only': True}}

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
    context_data = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalQueue
        fields = '__all__'

    def get_context_data(self, obj):
        """SRS 3.15: the reviewer must see the lead context and the proposed action,
        not just an opaque item id."""
        try:
            if obj.item_type == 'message_draft':
                message = Message.objects.select_related('lead').filter(id=obj.item_id).first()
                if not message:
                    return None
                lead = message.lead
                return {
                    'kind': 'message_draft',
                    'subject': message.subject,
                    'body': message.body,
                    'lead_name': f"{lead.first_name or ''} {lead.last_name or ''}".strip() or lead.email,
                    'lead_email': lead.email,
                    'lead_title': lead.title,
                    'lead_score': lead.lead_score,
                    'score_reason': lead.score_reason,
                }
            if obj.item_type == 'reply_review':
                reply = Reply.objects.select_related('lead').filter(id=obj.item_id).first()
                if not reply:
                    return None
                lead = reply.lead
                return {
                    'kind': 'reply_review',
                    'body': reply.body,
                    'category': reply.category,
                    'sentiment': reply.sentiment,
                    'confidence': reply.confidence,
                    'summary': reply.summary,
                    'next_action': reply.next_action,
                    'lead_name': f"{lead.first_name or ''} {lead.last_name or ''}".strip() or lead.email,
                    'lead_email': lead.email,
                    'lead_title': lead.title,
                    'lead_score': lead.lead_score,
                    'score_reason': lead.score_reason,
                }
        except (ValueError, ValidationError):
            return None
        return None

class LinkedInTaskSerializer(serializers.ModelSerializer):
    lead_name = serializers.SerializerMethodField()
    lead_linkedin_url = serializers.SerializerMethodField()

    class Meta:
        model = LinkedInTask
        fields = '__all__'

    def get_lead_name(self, obj):
        if obj.lead:
            return f"{obj.lead.first_name or ''} {obj.lead.last_name or ''}".strip() or obj.lead.email
        return "Unknown"

    def get_lead_linkedin_url(self, obj):
        return obj.lead.linkedin_url if obj.lead else None

class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'

class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = '__all__'

class LeadMagnetSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadMagnetSubmission
        fields = '__all__'
        read_only_fields = ['lead']
