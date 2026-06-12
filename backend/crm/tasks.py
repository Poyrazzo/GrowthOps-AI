import urllib.parse
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from scraper.static import StaticScraper
from scraper.dynamic import DynamicScraper
from scraper.cleaner import DataCleaner
from crm.models import (
    Lead, Campaign, Company, Message, EmailAccount, Reply,
    SuppressionList, ApprovalQueue, LeadSource, LeadMagnet, LinkedInTask
)
from crm.utils import send_notification_webhook, log_activity, FREE_EMAIL_PROVIDERS
from ai_engine.company_profiler import extract_company_info
from ai_engine.lead_profiler import score_lead
from ai_engine.email_generator import generate_email_draft
from ai_engine.linkedin_generator import generate_connection_request, generate_dm_draft
from ai_engine.reply_classifier import classify_reply
from outreach.imap import IMAPReader
from outreach.sequence import dispatch_pending_emails, process_followups


def _resolve_company(email: str, page_company: Company, page_domain: str):
    """Attributes a lead to the right Company.

    Corporate email domains always win (a lead found on a directory belongs to the
    company in their email address, NOT to the directory site). Free mailbox
    providers tell us nothing, so those leads fall back to the page's company,
    which is None for directory sources.
    """
    if email and '@' in email:
        domain = email.split('@', 1)[1].lower()
        if domain in FREE_EMAIL_PROVIDERS:
            return page_company
        if page_company and domain == page_domain:
            return page_company
        company, _ = Company.objects.get_or_create(domain=domain, defaults={'name': domain})
        return company
    return page_company


def _process_and_save_scrape_result(result: dict, campaign_id: str = None, source_id: str = None) -> dict:
    """Fans out the raw scraper result, cleans it, and saves it to the DB."""
    if not result.get('success'):
        return {"success": False, "error": "Scrape failed or returned empty HTML.", "processed": 0, "saved": 0}

    url = result.get('url', '')
    page_domain = urllib.parse.urlparse(url).netloc.lower()
    if page_domain.startswith('www.'):
        page_domain = page_domain[4:]

    source = LeadSource.objects.filter(id=source_id).first() if source_id else None
    source_type = source.source_type if source else None

    # Directory/listing pages are not companies our leads work for, so we never
    # attach leads to them or enrich them as if they were the lead's employer.
    page_company = None
    if page_domain and source_type != 'directory':
        page_company, _ = Company.objects.get_or_create(domain=page_domain, defaults={'name': page_domain})
        linkedin_company = result.get('social_links', {}).get('linkedin_company')
        if linkedin_company and not page_company.linkedin_url:
            page_company.linkedin_url = linkedin_company
            page_company.save()

    raw_leads = [{'email': email} for email in result.get('emails', [])]
    for profile_url in result.get('social_links', {}).get('linkedin_profiles', []):
        raw_leads.append({'email': None, 'linkedin_url': profile_url})

    cleaner = DataCleaner(raw_leads)
    cleaned_leads = cleaner.process()

    saved_count = 0
    campaign = Campaign.objects.filter(id=campaign_id).first() if campaign_id else None
    leads_to_score = []

    for lead_data in cleaned_leads:
        email = lead_data.get('email')
        linkedin_url = lead_data.get('linkedin_url')
        if not email and not linkedin_url:
            continue

        company = _resolve_company(email, page_company, page_domain)

        lead = None
        if email:
            lead = Lead.objects.filter(email=email).first()
        if not lead and linkedin_url:
            lead = Lead.objects.filter(linkedin_url=linkedin_url).first()

        if not lead:
            lead = Lead.objects.create(
                email=email,
                linkedin_url=linkedin_url,
                first_name=lead_data.get('first_name'),
                last_name=lead_data.get('last_name'),
                campaign=campaign,
                company=company,
                source=source,
                is_generic_email=bool(lead_data.get('is_generic_email')),
                status='uncontacted'
            )
            saved_count += 1
            log_activity(lead, 'lead_created', f"Scraped from {url}", {"source_url": url})
            # Leads not tied to the page's own company won't be reached by the
            # page-company enrichment fan-out below, so score them directly.
            if not page_company or lead.company_id != page_company.id:
                leads_to_score.append(str(lead.id))
        else:
            updated = False
            if linkedin_url and not lead.linkedin_url:
                lead.linkedin_url = linkedin_url
                updated = True
            if company and not lead.company:
                lead.company = company
                updated = True
            if updated:
                lead.save()

    if source:
        source.last_scraped_at = timezone.now()
        source.save(update_fields=['last_scraped_at'])

    body_text = result.get('body_text', '')
    if page_company:
        enrich_company_task.delay(str(page_company.id), body_text)
    for lead_id in leads_to_score:
        score_lead_task.delay(lead_id)

    return {
        "success": True,
        "processed": len(cleaned_leads),
        "saved": saved_count,
        "campaign_id": campaign_id
    }

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def run_static_scrape(self, url: str, campaign_id: str = None, proxy_url: str = None, source_id: str = None):
    """Executes a static scrape in the background on the default Celery queue."""
    scraper = StaticScraper()
    result = scraper.scrape_website(url, proxy_url=proxy_url)
    return _process_and_save_scrape_result(result, campaign_id, source_id)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3, queue='playwright')
def run_dynamic_scrape(self, url: str, campaign_id: str = None, adspower_profile_id: str = None, proxy_url: str = None, source_id: str = None):
    """Executes a dynamic scrape explicitly on the isolated playwright_worker container."""
    scraper = DynamicScraper()
    result = scraper.scrape_website(url, adspower_profile_id=adspower_profile_id, proxy_url=proxy_url)
    return _process_and_save_scrape_result(result, campaign_id, source_id)

@shared_task
def trigger_scheduled_scrapes_task():
    """Beat task: walks active campaigns and enqueues scrapes for their due LeadSources.

    This is the missing glue between 'operator configures Campaign + Sources' and
    'scraping actually happens'. LinkedIn-type sources are NEVER auto-scraped
    (human-in-the-loop compliance rule).
    """
    today = timezone.now().date()
    refresh_cutoff = timezone.now() - timezone.timedelta(hours=settings.SCRAPE_REFRESH_HOURS)

    campaigns = Campaign.objects.filter(status='active')
    triggered = 0
    for campaign in campaigns:
        if campaign.start_date and campaign.start_date > today:
            continue
        if campaign.end_date and campaign.end_date < today:
            continue

        sources = campaign.sources.exclude(source_type='linkedin').order_by('-priority_score')
        for source in sources:
            if source.last_scraped_at and source.last_scraped_at > refresh_cutoff:
                continue
            # Stamp immediately so overlapping beat runs don't double-trigger
            source.last_scraped_at = timezone.now()
            source.save(update_fields=['last_scraped_at'])

            if source.source_type == 'dynamic':
                run_dynamic_scrape.delay(source.url, campaign_id=str(campaign.id), source_id=str(source.id))
            else:
                run_static_scrape.delay(source.url, campaign_id=str(campaign.id), source_id=str(source.id))
            triggered += 1

    return f"Triggered {triggered} scrapes"

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def enrich_company_task(self, company_id: str, body_text: str):
    """Uses LLM to extract company profile from scraped text."""
    company = Company.objects.filter(id=company_id).first()
    if not company:
        return "Company not found"

    if not company.value_proposition and body_text:
        info = extract_company_info(company.domain, body_text)
        if info:
            company.name = info.get('name') or company.name
            company.sector = info.get('sector') or company.sector
            company.size = info.get('size') or company.size
            company.location = info.get('location') or company.location
            company.value_proposition = info.get('value_proposition') or company.value_proposition
            company.save()

    leads = Lead.objects.filter(company=company, score_reason='')
    for lead in leads:
        score_lead_task.delay(str(lead.id))

    return f"Enriched company {company.name}"

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def score_lead_task(self, lead_id: str):
    """Uses LLM to score a lead, assign a persona, match a lead magnet, and recommend an angle."""
    lead = Lead.objects.filter(id=lead_id).first()
    if not lead:
        return "Lead not found"

    campaign_persona = lead.campaign.target_persona if lead.campaign else "Any B2B prospect"
    company_vp = lead.company.value_proposition if lead.company else None

    magnets = list(LeadMagnet.objects.all().values('name', 'description', 'target_persona'))

    score_data = score_lead(
        lead_title=lead.title,
        company_vp=company_vp,
        campaign_persona=campaign_persona,
        available_lead_magnets=magnets,
        is_generic_email=lead.is_generic_email,
        company_name=lead.company.name if lead.company else None
    )

    if score_data:
        lead.lead_score = score_data.get('score', 0)
        lead.score_reason = score_data.get('reasoning', '')
        lead.persona = score_data.get('persona', '') or lead.persona
        lead.recommended_message_angle = score_data.get('recommended_message_angle', '')

        magnet_name = (score_data.get('recommended_lead_magnet') or '').strip()
        if magnet_name:
            lead.recommended_lead_magnet = LeadMagnet.objects.filter(name__iexact=magnet_name).first()

        lead.save()
        log_activity(lead, 'lead_scored', f"Scored {lead.lead_score}/100", {"reason": lead.score_reason})

        # Auto-outreach only fires for leads above threshold inside an ACTIVE campaign,
        # routed by the campaign's channel (email draft vs manual LinkedIn task).
        campaign = lead.campaign
        if (lead.lead_score >= settings.LEAD_SCORE_THRESHOLD
                and campaign and campaign.status == 'active'):
            if campaign.outreach_channel == 'linkedin':
                generate_linkedin_task_task.delay(str(lead.id))
            else:
                generate_draft_task.delay(str(lead.id))

    return f"Scored lead {lead.email or lead.linkedin_url} with score {lead.lead_score}"

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def generate_draft_task(self, lead_id: str):
    """Uses LLM to draft a personalized email and saves it to the database."""
    lead = Lead.objects.filter(id=lead_id).first()
    if not lead or not lead.campaign:
        return "Lead or campaign not found"

    if not lead.email:
        return "Lead has no email address"

    # An initial draft already exists in any live state (pending review, queued, or sent)
    if Message.objects.filter(lead=lead, channel='email').exclude(status__in=['failed', 'cancelled']).exists():
        return "Draft already exists for this lead"

    company_name = lead.company.name if lead.company else "Unknown"
    company_vp = lead.company.value_proposition if lead.company else "Unknown"

    if lead.recommended_lead_magnet:
        magnet = lead.recommended_lead_magnet
        lead_magnet_desc = f"{magnet.name}: {magnet.description} ({magnet.url})"
    else:
        lead_magnet_desc = lead.campaign.lead_magnet or "None"

    draft_data = generate_email_draft(
        lead_name=lead.first_name,
        lead_title=lead.title,
        company_name=company_name,
        company_vp=company_vp,
        campaign_vp=lead.campaign.value_proposition,
        message_angle=lead.recommended_message_angle,
        lead_magnet=lead_magnet_desc,
        is_generic_email=lead.is_generic_email,
        sender_name=lead.campaign.name
    )

    if draft_data and draft_data.get('subject') and draft_data.get('body'):
        status = 'needs_review' if lead.requires_human_review else 'pending'

        message = Message.objects.create(
            lead=lead,
            campaign=lead.campaign,
            channel='email',
            subject=draft_data['subject'],
            body=draft_data['body'],
            status=status
        )
        log_activity(lead, 'draft_created', f"AI drafted: {message.subject}")

        if status == 'needs_review':
            ApprovalQueue.objects.create(
                item_type='message_draft',
                item_id=str(message.id),
                status='pending',
                reason_for_review=f"AI drafted an email for {lead.email}."
            )

        return f"Drafted email for {lead.email}"
    return "Failed to draft email"

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def generate_linkedin_task_task(self, lead_id: str):
    """Creates a manual LinkedIn 'connect' task with an AI-drafted connection note (SRS 3.14)."""
    lead = Lead.objects.filter(id=lead_id).first()
    if not lead or not lead.campaign:
        return "Lead or campaign not found"

    if not lead.linkedin_url:
        return "Lead has no LinkedIn profile URL"

    if LinkedInTask.objects.filter(lead=lead, status='pending').exists():
        return "Pending LinkedIn task already exists for this lead"

    draft = generate_connection_request(
        lead_name=lead.first_name,
        lead_title=lead.title,
        company_name=lead.company.name if lead.company else None,
        campaign_vp=lead.campaign.value_proposition,
        message_angle=lead.recommended_message_angle
    )

    if draft and draft.get('connection_message'):
        task = LinkedInTask.objects.create(
            lead=lead,
            campaign=lead.campaign,
            task_type='connect',
            status='pending',
            instructions=(
                f"Open {lead.linkedin_url} and send a connection request with this note:\n\n"
                f"{draft['connection_message']}"
            )
        )
        log_activity(lead, 'linkedin_task_created', "AI drafted connection request", {"task_id": str(task.id)})
        return f"Created LinkedIn connect task for {lead.linkedin_url}"
    return "Failed to draft connection request"

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def generate_linkedin_dm_task(self, lead_id: str):
    """After a connection is accepted (connect task completed), drafts the manual DM task (SRS 3.14)."""
    lead = Lead.objects.filter(id=lead_id).first()
    if not lead or not lead.campaign:
        return "Lead or campaign not found"

    if LinkedInTask.objects.filter(lead=lead, task_type='message', status='pending').exists():
        return "Pending DM task already exists for this lead"

    if lead.recommended_lead_magnet:
        magnet_desc = f"{lead.recommended_lead_magnet.name} ({lead.recommended_lead_magnet.url})"
    else:
        magnet_desc = lead.campaign.lead_magnet

    draft = generate_dm_draft(
        lead_name=lead.first_name,
        lead_title=lead.title,
        company_name=lead.company.name if lead.company else None,
        campaign_vp=lead.campaign.value_proposition,
        message_angle=lead.recommended_message_angle,
        lead_magnet=magnet_desc
    )

    if draft and draft.get('dm_message'):
        task = LinkedInTask.objects.create(
            lead=lead,
            campaign=lead.campaign,
            task_type='message',
            status='pending',
            instructions=(
                f"The connection was accepted. Open {lead.linkedin_url} and send this DM:\n\n"
                f"{draft['dm_message']}"
            )
        )
        log_activity(lead, 'linkedin_task_created', "AI drafted follow-up DM", {"task_id": str(task.id)})
        return f"Created LinkedIn DM task for {lead.linkedin_url}"
    return "Failed to draft DM"

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def poll_single_inbox_task(self, account_id: str):
    """Connects to a single IMAP inbox and reads replies."""
    account = EmailAccount.objects.filter(id=account_id, is_active=True).first()
    if not account:
        return "Account not found or inactive"

    reader = IMAPReader(account)
    processed = reader.read_inbox()
    return f"Processed {processed} replies for {account.email}"

@shared_task
def poll_all_inboxes_task():
    """Fans out the inbox polling task to all active email accounts."""
    accounts = EmailAccount.objects.filter(is_active=True).exclude(imap_host__isnull=True).exclude(imap_host__exact='')
    count = 0
    for account in accounts:
        poll_single_inbox_task.delay(str(account.id))
        count += 1
    return f"Triggered polling for {count} accounts"

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def classify_reply_task(self, reply_id: str):
    """Uses LLM to classify a newly received reply and applies auto-suppression if needed."""
    reply = Reply.objects.filter(id=reply_id).first()
    if not reply:
        return "Reply not found"

    original_body = reply.message.body if reply.message else ""
    classification = classify_reply(reply.body, original_body)
    if not classification:
        # Raise so Celery's autoretry kicks in instead of silently dropping the reply
        raise ValueError(f"Empty classification result for reply {reply_id}")

    reply.category = classification.get('category')
    reply.sentiment = classification.get('sentiment')
    reply.confidence = classification.get('confidence')
    reply.summary = classification.get('summary')
    reply.next_action = classification.get('next_action')
    reply.save()

    lead = reply.lead
    log_activity(lead, 'reply_classified', f"{reply.category} ({reply.sentiment})", {
        "confidence": reply.confidence, "summary": reply.summary
    })

    # SRS 3.13: low-confidence classifications must be reviewed by a human
    if reply.confidence is not None and reply.confidence < settings.REPLY_CONFIDENCE_THRESHOLD:
        ApprovalQueue.objects.get_or_create(
            item_type='reply_review',
            item_id=str(reply.id),
            defaults={
                'status': 'pending',
                'reason_for_review': (
                    f"AI classified reply from {lead.email} as '{reply.category}' with low "
                    f"confidence ({reply.confidence:.2f}). Summary: {reply.summary}"
                )
            }
        )

    if reply.category in ['unsubscribe', 'bounce']:
        if lead.email:
            SuppressionList.objects.get_or_create(
                email=lead.email,
                defaults={'reason': 'unsubscribed' if reply.category == 'unsubscribe' else 'bounced'}
            )
            log_activity(lead, 'lead_suppressed', f"Auto-suppressed: {reply.category}")
        lead.status = 'disqualified'
        lead.save()
    else:
        # Any genuine human reply halts the sequence (SRS 3.10 stop condition)
        if lead.status != 'replied':
            lead.status = 'replied'
            lead.save()

        if reply.sentiment == 'positive':
            send_notification_webhook(
                event_type="positive_reply",
                payload={
                    "lead_email": lead.email,
                    "lead_name": f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
                    "sentiment": reply.sentiment,
                    "message_body": reply.body
                }
            )

    return f"Classified reply {reply.id} as {reply.category}"

@shared_task
def dispatch_emails_task():
    """Dispatches all pending messages via SMTP."""
    count = dispatch_pending_emails()
    return f"Dispatched {count} emails"

@shared_task
def process_followups_task():
    """Checks all leads in sequence and generates follow-ups if 3 days have passed."""
    count = process_followups()
    return f"Generated {count} follow-up drafts"
