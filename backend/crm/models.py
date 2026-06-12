import uuid
from django.db import models

class Campaign(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed')
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    target_sector = models.CharField(max_length=255)
    target_country = models.CharField(max_length=100)
    target_persona = models.CharField(max_length=255)
    value_proposition = models.TextField()
    lead_magnet = models.CharField(max_length=255, blank=True, null=True)
    outreach_channel = models.CharField(max_length=50, choices=[('email', 'Email'), ('linkedin', 'LinkedIn')])
    success_metric = models.CharField(max_length=255, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='draft')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class LeadSource(models.Model):
    SOURCE_TYPES = [
        ('static', 'Static Website'),
        ('dynamic', 'Dynamic Website'),
        ('linkedin', 'LinkedIn'),
        ('directory', 'Directory')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(unique=True, max_length=500)
    source_type = models.CharField(max_length=50, choices=SOURCE_TYPES)
    sector = models.CharField(max_length=255)
    expected_data_fields = models.JSONField(default=dict, blank=True)
    access_rules = models.TextField(blank=True)
    priority_score = models.IntegerField(default=0)
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name='sources')
    last_scraped_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.url

class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, unique=True, blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    sector = models.CharField(max_length=255, blank=True, null=True)
    size = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    value_proposition = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Lead(models.Model):
    STATUS_CHOICES = [
        ('uncontacted', 'Uncontacted'),
        ('in_sequence', 'In Sequence'),
        ('replied', 'Replied'),
        ('disqualified', 'Disqualified')
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, blank=True, null=True)
    first_name = models.CharField(max_length=150, blank=True, null=True)
    last_name = models.CharField(max_length=150, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    profile_url = models.URLField(blank=True, null=True)

    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    source = models.ForeignKey(LeadSource, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')

    persona = models.CharField(max_length=255, blank=True, null=True)
    department = models.CharField(max_length=150, blank=True, null=True)
    lead_score = models.IntegerField(default=0)
    score_reason = models.TextField(blank=True)
    recommended_message_angle = models.TextField(blank=True)
    recommended_lead_magnet = models.ForeignKey('LeadMagnet', on_delete=models.SET_NULL, null=True, blank=True, related_name='recommended_leads')
    is_generic_email = models.BooleanField(default=False)
    requires_human_review = models.BooleanField(default=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='uncontacted')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    class Meta:
        constraints = [
            # email already carries unique=True; linkedin_url must be unique only when present
            # (NULLs are never equal in Postgres, so the old combined constraint enforced nothing useful)
            models.UniqueConstraint(
                fields=['linkedin_url'],
                condition=models.Q(linkedin_url__isnull=False),
                name='unique_lead_linkedin'
            ),
            models.UniqueConstraint(
                fields=['profile_url'],
                condition=models.Q(profile_url__isnull=False) & ~models.Q(profile_url=''),
                name='unique_lead_profile_url'
            )
        ]

class EmailAccount(models.Model):
    ENCRYPTION_CHOICES = [
        ('tls', 'STARTTLS'),
        ('ssl', 'SSL/TLS'),
        ('none', 'None (local/mock servers only)')
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    provider = models.CharField(max_length=100)
    smtp_host = models.CharField(max_length=255, blank=True, null=True)
    smtp_port = models.IntegerField(blank=True, null=True)
    smtp_encryption = models.CharField(max_length=10, choices=ENCRYPTION_CHOICES, default='tls')
    imap_host = models.CharField(max_length=255, blank=True, null=True)
    imap_port = models.IntegerField(default=993, blank=True, null=True)
    imap_use_ssl = models.BooleanField(default=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    password_encrypted = models.CharField(max_length=500, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    daily_limit = models.IntegerField(default=100)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.password_encrypted and not self.password_encrypted.startswith('gAAAAAB'):
            from core.encryption import encrypt
            self.password_encrypted = encrypt(self.password_encrypted)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

class LeadMagnet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    url = models.URLField()
    target_persona = models.CharField(max_length=255, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Message(models.Model):
    STATUS_CHOICES = [
        ('needs_review', 'Needs Review'),
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
        ('cancelled', 'Cancelled')
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='messages')
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='messages')
    sender_account = models.ForeignKey(EmailAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    channel = models.CharField(max_length=50, choices=[('email', 'Email'), ('linkedin', 'LinkedIn')])
    message_id = models.CharField(max_length=255, blank=True, null=True)
    subject = models.CharField(max_length=500, blank=True, null=True)
    body = models.TextField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Message to {self.lead} via {self.channel}"

class Reply(models.Model):
    CATEGORY_CHOICES = [
        ('interested', 'Interested'),
        ('not_interested', 'Not Interested'),
        ('meeting_request', 'Meeting Request'),
        ('price_question', 'Price Question'),
        ('unsubscribe', 'Unsubscribe'),
        ('bounce', 'Bounce'),
        ('wrong_person', 'Wrong Person'),
        ('other', 'Other')
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='replies')
    message = models.ForeignKey(Message, on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    body = models.TextField()
    received_at = models.DateTimeField()
    
    # AI Classification Fields
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True, null=True)
    sentiment = models.CharField(max_length=50, blank=True, null=True)
    confidence = models.FloatField(blank=True, null=True)
    summary = models.TextField(blank=True, null=True)
    next_action = models.CharField(max_length=255, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reply from {self.lead} - {self.category}"

class SuppressionList(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(blank=True, null=True)
    domain = models.CharField(max_length=255, blank=True, null=True)
    reason = models.CharField(max_length=50, choices=[
        ('bounced', 'Bounced'),
        ('unsubscribed', 'Unsubscribed'),
        ('manual_block', 'Manual Block')
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email or self.domain or "Unknown"

class ApprovalQueue(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item_type = models.CharField(max_length=100) # e.g., 'message_draft', 'lead_classification'
    item_id = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    reason_for_review = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.item_type} - {self.status}"

class LinkedInTask(models.Model):
    TASK_TYPES = [
        ('connect', 'Connect'),
        ('message', 'Message'),
        ('engagement', 'Engagement')
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='linkedin_tasks')
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='linkedin_tasks')
    task_type = models.CharField(max_length=50, choices=TASK_TYPES)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    instructions = models.TextField(blank=True)
    due_date = models.DateField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.task_type} task for {self.lead}"

class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=255)
    resource_type = models.CharField(max_length=100)
    resource_id = models.CharField(max_length=255)
    details = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} on {self.resource_type} ({self.resource_id})"

class Activity(models.Model):
    ACTIVITY_TYPES = [
        ('lead_created', 'Lead Created'),
        ('lead_enriched', 'Lead Enriched'),
        ('lead_scored', 'Lead Scored'),
        ('draft_created', 'Draft Created'),
        ('email_sent', 'Email Sent'),
        ('reply_received', 'Reply Received'),
        ('reply_classified', 'Reply Classified'),
        ('linkedin_task_created', 'LinkedIn Task Created'),
        ('linkedin_task_completed', 'LinkedIn Task Completed'),
        ('lead_magnet_submitted', 'Lead Magnet Submitted'),
        ('lead_suppressed', 'Lead Suppressed'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='activities')
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Activities'

    def __str__(self):
        return f"{self.activity_type} - {self.lead}"

class LeadMagnetSubmission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead_magnet = models.ForeignKey(LeadMagnet, on_delete=models.CASCADE, related_name='submissions')
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True, related_name='magnet_submissions')
    email = models.EmailField()
    form_data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email} -> {self.lead_magnet.name}"
