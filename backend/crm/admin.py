from django.contrib import admin
from .models import (
    Campaign, LeadSource, Company, Lead, EmailAccount, LeadMagnet, Message, Reply,
    SuppressionList, ApprovalQueue, LinkedInTask, AuditLog, Activity, LeadMagnetSubmission
)

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'target_sector', 'outreach_channel', 'start_date', 'end_date', 'created_at')
    search_fields = ('name', 'target_sector')
    list_filter = ('outreach_channel',)

@admin.register(LeadSource)
class LeadSourceAdmin(admin.ModelAdmin):
    list_display = ('url', 'source_type', 'sector', 'priority_score', 'created_at')
    search_fields = ('url', 'sector')
    list_filter = ('source_type',)

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'sector', 'size', 'location')
    search_fields = ('name', 'domain')

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'company', 'lead_score', 'requires_human_review')
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('requires_human_review', 'campaign')

@admin.register(EmailAccount)
class EmailAccountAdmin(admin.ModelAdmin):
    list_display = ('email', 'provider', 'is_active', 'daily_limit')
    search_fields = ('email',)
    list_filter = ('is_active', 'provider')

@admin.register(LeadMagnet)
class LeadMagnetAdmin(admin.ModelAdmin):
    list_display = ('name', 'target_persona', 'created_at')
    search_fields = ('name', 'target_persona')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('lead', 'campaign', 'channel', 'status', 'sent_at')
    search_fields = ('lead__email', 'subject')
    list_filter = ('status', 'channel', 'campaign')

@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ('lead', 'category', 'confidence', 'received_at')
    search_fields = ('lead__email', 'body')
    list_filter = ('category',)

@admin.register(SuppressionList)
class SuppressionListAdmin(admin.ModelAdmin):
    list_display = ('email', 'domain', 'reason', 'created_at')
    search_fields = ('email', 'domain')
    list_filter = ('reason',)

@admin.register(ApprovalQueue)
class ApprovalQueueAdmin(admin.ModelAdmin):
    list_display = ('item_type', 'item_id', 'status', 'created_at')
    search_fields = ('item_type', 'item_id')
    list_filter = ('status', 'item_type')

@admin.register(LinkedInTask)
class LinkedInTaskAdmin(admin.ModelAdmin):
    list_display = ('task_type', 'lead', 'campaign', 'status', 'due_date')
    search_fields = ('lead__email', 'lead__first_name')
    list_filter = ('status', 'task_type', 'campaign')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'resource_type', 'resource_id', 'created_at')
    search_fields = ('action', 'resource_type', 'resource_id')
    list_filter = ('resource_type', 'action')

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('activity_type', 'lead', 'campaign', 'created_at')
    search_fields = ('lead__email', 'description')
    list_filter = ('activity_type', 'campaign')

@admin.register(LeadMagnetSubmission)
class LeadMagnetSubmissionAdmin(admin.ModelAdmin):
    list_display = ('email', 'lead_magnet', 'lead', 'created_at')
    search_fields = ('email', 'lead_magnet__name')
    list_filter = ('lead_magnet',)
