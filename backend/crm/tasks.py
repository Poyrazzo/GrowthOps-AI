import logging
import urllib.parse
from bs4 import BeautifulSoup
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from scraper.static import StaticScraper
from scraper.dynamic import DynamicScraper
from scraper.cleaner import DataCleaner
from scraper.extractor import extract_contacts, extract_social_links
from scraper.linkedin import scrape_linkedin_profile as _scrape_linkedin_profile, search_and_scrape_linkedin
from scraper.search import (
    discover_person_pages,
    is_linkedin_profile_url,
    parse_person_from_search_result,
)
from crm.models import (
    Lead, Campaign, Company, Message, EmailAccount, Reply,
    SuppressionList, ApprovalQueue, LeadSource, LeadMagnet, LinkedInTask
)
from crm.utils import send_notification_webhook, log_activity, FREE_EMAIL_PROVIDERS
from ai_engine.company_profiler import extract_company_info
from ai_engine.lead_profiler import looks_like_clear_non_person_name, score_lead
from ai_engine.email_generator import generate_email_draft
from ai_engine.linkedin_generator import generate_connection_request, generate_dm_draft
from ai_engine.reply_classifier import classify_reply
from outreach.imap import IMAPReader
from outreach.sequence import dispatch_pending_emails, process_followups

logger = logging.getLogger(__name__)


_ZERO_SCORE_BAD_DATA_MARKERS = (
    'non-person',
    'not a person',
    'bad data',
    'not human',
    'generic noun',
    'institution name',
    'product name',
    'unusable',
)


def _normalize_lead_score(lead: Lead, score_data: dict) -> tuple[int, str]:
    """Keep true junk at 0, but do not let uncertain scraped leads collapse to 0/100."""
    raw_score = score_data.get('score', 0)
    try:
        score = int(raw_score)
    except (TypeError, ValueError):
        score = 0

    score = max(0, min(100, score))
    reason = score_data.get('reasoning', '') or ''
    persona = score_data.get('persona', '') or ''
    combined = f"{reason} {persona}".lower()
    lead_name = ' '.join(filter(None, [lead.first_name, lead.last_name])) or None

    clear_bad_data = (
        looks_like_clear_non_person_name(lead_name)
        or any(marker in combined for marker in _ZERO_SCORE_BAD_DATA_MARKERS)
        or not (lead.email or lead.linkedin_url or lead.profile_url)
    )

    if score == 0 and not clear_bad_data:
        score = 35
        reason = (
            f"{reason} " if reason else ""
        ) + "Adjusted from 0 because the lead is contactable but not confirmed bad data; keep for manual review."

    return score, reason


def _resolve_pipeline_campaign(campaign_id: str = None, source: LeadSource = None):
    if campaign_id:
        return Campaign.objects.filter(id=campaign_id).first()
    if source and source.campaign_id:
        return source.campaign
    return None


def _campaign_allows_pipeline_work(campaign, campaign_id: str = None, task_name: str = "task") -> bool:
    if campaign:
        if campaign.status != 'active':
            logger.info(
                "%s skipped: campaign=%s status=%s is not active",
                task_name, campaign.id, campaign.status,
            )
            return False
        return True

    if campaign_id:
        logger.info("%s skipped: campaign=%s no longer exists", task_name, campaign_id)
        return False

    return True


def _refresh_campaign_allows_pipeline_work(campaign, campaign_id: str = None, task_name: str = "task") -> bool:
    if campaign:
        campaign.refresh_from_db(fields=['status'])
    return _campaign_allows_pipeline_work(campaign, campaign_id, task_name)


def _search_discovered_contacts(page_company: Company, page_domain: str, campaign: Campaign) -> list:
    """Use search to find public person/profile pages, then scrape those pages."""
    if not page_company or not getattr(settings, 'SEARCH_DISCOVERY_ENABLED', True):
        return []

    search_results = discover_person_pages(
        company_name=page_company.name,
        company_domain=page_domain,
        target_persona=campaign.target_persona if campaign else None,
        limit=getattr(settings, 'SEARCH_DISCOVERY_RESULT_LIMIT', 10),
    )
    if not search_results:
        return []

    scraper = StaticScraper(timeout=10)
    discovered = []
    for result in search_results:
        profile_url = result.get('url')
        if not profile_url:
            continue

        parsed_person = parse_person_from_search_result(result)
        if is_linkedin_profile_url(profile_url):
            discovered.append({
                'email': None,
                'linkedin_url': profile_url,
                'profile_url': profile_url,
                'first_name': parsed_person.get('first_name'),
                'last_name': parsed_person.get('last_name'),
                'title': parsed_person.get('title'),
            })
            continue

        html = scraper.fetch_html(profile_url)
        if not html:
            # For inaccessible pages, only save genuine LinkedIn /in/ profiles —
            # we can't verify other pages so we skip them to avoid saving page
            # titles (e.g. "İngilizce İlanları") as fake person names.
            if 'linkedin.com/in/' in profile_url:
                discovered.append({
                    'email': None,
                    'linkedin_url': profile_url,
                    'profile_url': profile_url,
                    'first_name': parsed_person.get('first_name'),
                    'last_name': parsed_person.get('last_name'),
                    'title': parsed_person.get('title'),
                })
            continue

        soup = BeautifulSoup(html, 'html.parser')
        contacts = extract_contacts(soup, html)
        if contacts:
            for contact in contacts:
                contact['profile_url'] = contact.get('profile_url') or profile_url
                discovered.append(contact)
        elif parsed_person.get('first_name') or parsed_person.get('last_name'):
            # Only save a profile URL lead if we could at least parse a name from the result
            discovered.append({
                'email': None,
                'linkedin_url': None,
                'profile_url': profile_url,
                'first_name': parsed_person.get('first_name'),
                'last_name': parsed_person.get('last_name'),
                'title': parsed_person.get('title'),
            })

        for linkedin_url in extract_social_links(soup).get('linkedin_profiles', []):
            discovered.append({
                'email': None,
                'linkedin_url': linkedin_url,
                'profile_url': profile_url,
                'first_name': parsed_person.get('first_name'),
                'last_name': parsed_person.get('last_name'),
                'title': parsed_person.get('title'),
            })

    logger.info(
        "SEARCH DISCOVERY company=%s results=%d contacts=%d",
        page_company.name, len(search_results), len(discovered)
    )
    return discovered


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
        logger.error("SCRAPE FAILED url=%s campaign=%s source=%s", result.get('url'), campaign_id, source_id)
        return {"success": False, "error": "Scrape failed or returned empty HTML.", "processed": 0, "saved": 0}

    logger.info("SCRAPE SUCCESS url=%s contacts=%d campaign=%s source=%s",
                result.get('url'), len(result.get('contacts') or result.get('emails', [])),
                campaign_id, source_id)

    url = result.get('url', '')
    page_domain = urllib.parse.urlparse(url).netloc.lower()
    if page_domain.startswith('www.'):
        page_domain = page_domain[4:]

    source = LeadSource.objects.select_related('campaign').filter(id=source_id).first() if source_id else None
    source_type = source.source_type if source else None
    campaign = _resolve_pipeline_campaign(campaign_id, source)
    if not _campaign_allows_pipeline_work(campaign, campaign_id, "_process_and_save_scrape_result"):
        return {"success": True, "processed": 0, "saved": 0, "skipped": "Campaign is not active."}

    # Directory/listing pages are not companies our leads work for, so we never
    # attach leads to them or enrich them as if they were the lead's employer.
    page_company = None
    if page_domain and source_type != 'directory':
        page_company, _ = Company.objects.get_or_create(domain=page_domain, defaults={'name': page_domain})
        linkedin_company = result.get('social_links', {}).get('linkedin_company')
        if linkedin_company and not page_company.linkedin_url:
            page_company.linkedin_url = linkedin_company
            page_company.save()

    # Prefer the richer 'contacts' (email/linkedin + extracted names/titles)
    # when the scraper provides them; fall back to bare emails for older paths.
    contacts = result.get('contacts')
    if contacts:
        raw_leads = [
            {'email': c.get('email'),
             'linkedin_url': c.get('linkedin_url'),
             'profile_url': c.get('profile_url'),
             'first_name': c.get('first_name'),
             'last_name': c.get('last_name'),
             'title': c.get('title')}
            for c in contacts
        ]
    else:
        raw_leads = [{'email': email} for email in result.get('emails', [])]
    for profile_url in result.get('social_links', {}).get('linkedin_profiles', []):
        raw_leads.append({'email': None, 'linkedin_url': profile_url, 'profile_url': profile_url})

    raw_leads.extend(_search_discovered_contacts(page_company, page_domain, campaign))

    cleaner = DataCleaner(raw_leads)
    cleaned_leads = cleaner.process()
    if not getattr(settings, 'SAVE_GENERIC_EMAIL_LEADS', False):
        before_count = len(cleaned_leads)

        def _looks_like_email_only_human(lead):
            return bool(
                lead.get('email')
                and not lead.get('linkedin_url')
                and not lead.get('profile_url')
                and (lead.get('last_name') or lead.get('title'))
            )

        def _looks_like_profile_human(lead):
            return bool(
                lead.get('profile_url')
                and (lead.get('first_name') or lead.get('last_name') or lead.get('title'))
            )

        def _looks_like_named_linkedin(lead):
            # A LinkedIn URL alone is only useful if we have at least a name to go with it
            return bool(
                lead.get('linkedin_url')
                and (lead.get('first_name') or lead.get('last_name') or lead.get('email'))
            )

        cleaned_leads = [
            lead for lead in cleaned_leads
            if _looks_like_named_linkedin(lead)
            or _looks_like_profile_human(lead)
            or (not lead.get('is_generic_email') and _looks_like_email_only_human(lead))
        ]
        skipped = before_count - len(cleaned_leads)
        if skipped:
            logger.info("Skipped %d generic/low-confidence email-only leads for %s", skipped, url)

    saved_count = 0
    leads_to_score = set()

    for lead_data in cleaned_leads:
        email = lead_data.get('email')
        linkedin_url = lead_data.get('linkedin_url')
        profile_url = lead_data.get('profile_url')
        if not email and not linkedin_url and not profile_url:
            continue
        lead_name = ' '.join(
            part for part in [lead_data.get('first_name'), lead_data.get('last_name')]
            if part
        )
        if looks_like_clear_non_person_name(lead_name):
            logger.info(
                "Skipped non-person scraped lead name=%r url=%s campaign=%s source=%s",
                lead_name, url, campaign_id, source_id,
            )
            continue

        company = _resolve_company(email, page_company, page_domain)

        lead = None
        if email:
            lead = Lead.objects.filter(email=email).first()
        if not lead and linkedin_url:
            lead = Lead.objects.filter(linkedin_url=linkedin_url).first()
        if not lead and profile_url:
            lead = Lead.objects.filter(profile_url=profile_url).first()

        if not lead:
            lead = Lead.objects.create(
                email=email,
                linkedin_url=linkedin_url,
                profile_url=profile_url,
                first_name=lead_data.get('first_name'),
                last_name=lead_data.get('last_name'),
                title=lead_data.get('title'),
                campaign=campaign,
                company=company,
                source=source,
                is_generic_email=bool(lead_data.get('is_generic_email')),
                status='uncontacted'
            )
            saved_count += 1
            logger.info("LEAD CREATED email=%s title=%s campaign=%s source=%s",
                        email, lead_data.get('title'), campaign_id, source_id)
            log_activity(lead, 'lead_created', f"Scraped from {url}", {"source_url": url})
            # Queue LinkedIn enrichment if the lead has a LinkedIn URL and enrichment is on
            if (lead.linkedin_url or (lead.profile_url and 'linkedin.com' in (lead.profile_url or ''))):
                if getattr(settings, 'LINKEDIN_ENRICHMENT_ENABLED', False):
                    enrich_linkedin_lead_task.apply_async(
                        args=[str(lead.id)],
                        countdown=5,
                        queue='playwright',
                    )
            # Queue email enrichment for named leads without an email address.
            # Uses Hunter.io (if key configured) then falls back to pattern inference.
            if (not lead.email
                    and (lead.first_name or lead.last_name)
                    and getattr(settings, 'EMAIL_ENRICHMENT_ENABLED', True)):
                enrich_lead_email_task.apply_async(
                    args=[str(lead.id)],
                    countdown=15,  # let company enrichment run first so domain is set
                )
        else:
            updated = False
            if email and not lead.email:
                lead.email = email
                updated = True
            if linkedin_url and not lead.linkedin_url:
                lead.linkedin_url = linkedin_url
                updated = True
            if profile_url and not lead.profile_url:
                lead.profile_url = profile_url
                updated = True
            if lead_data.get('first_name') and not lead.first_name:
                lead.first_name = lead_data.get('first_name')
                updated = True
            if lead_data.get('last_name') and not lead.last_name:
                lead.last_name = lead_data.get('last_name')
                updated = True
            if lead_data.get('title') and not lead.title:
                lead.title = lead_data.get('title')
                updated = True
            if company and not lead.company:
                lead.company = company
                updated = True
            if source and not lead.source:
                lead.source = source
                updated = True
            if campaign and not lead.campaign:
                lead.campaign = campaign
                updated = True
            if lead_data.get('is_generic_email') != lead.is_generic_email:
                lead.is_generic_email = bool(lead_data.get('is_generic_email'))
                updated = True
            if updated:
                lead.save()
                # If the lead now has a name but still no email, try email enrichment
                if (not lead.email
                        and (lead.first_name or lead.last_name)
                        and getattr(settings, 'EMAIL_ENRICHMENT_ENABLED', True)):
                    enrich_lead_email_task.apply_async(args=[str(lead.id)], countdown=15)

        if lead and not lead.score_reason:
            leads_to_score.add(str(lead.id))

    if source:
        source.last_scraped_at = timezone.now()
        source.save(update_fields=['last_scraped_at'])

    body_text = result.get('body_text', '')
    if page_company:
        enrich_company_task.delay(str(page_company.id), body_text)
    for lead_id in leads_to_score:
        score_lead_task.delay(lead_id)

    logger.info("SCRAPE RESULT url=%s processed=%d saved=%d campaign=%s",
                result.get('url'), len(cleaned_leads), saved_count, campaign_id)
    return {
        "success": True,
        "processed": len(cleaned_leads),
        "saved": saved_count,
        "campaign_id": campaign_id
    }

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def run_static_scrape(self, url: str, campaign_id: str = None, proxy_url: str = None, source_id: str = None):
    """Static scrape on the default queue. If a static fetch succeeds but finds no
    contacts, the page is likely JS-rendered — automatically retry with the
    Playwright (dynamic) scraper before giving up."""
    logger.info("TASK run_static_scrape START url=%s campaign=%s source=%s", url, campaign_id, source_id)
    source = LeadSource.objects.select_related('campaign').filter(id=source_id).first() if source_id else None
    campaign = _resolve_pipeline_campaign(campaign_id, source)
    if not _campaign_allows_pipeline_work(campaign, campaign_id, "run_static_scrape"):
        return {"success": True, "processed": 0, "saved": 0, "skipped": "Campaign is not active."}

    is_directory = source and source.source_type == 'directory'
    scraper = StaticScraper()
    result = scraper.scrape_website(url, proxy_url=proxy_url, is_directory=is_directory)

    no_contacts = (
        not result.get('contacts') and
        not result.get('emails') and
        not result.get('social_links', {}).get('linkedin_profiles')
    )
    if no_contacts:
        if not _refresh_campaign_allows_pipeline_work(campaign, campaign_id, "run_static_scrape dynamic handoff"):
            return {"success": True, "processed": 0, "saved": 0, "skipped": "Campaign is not active."}
        logger.info("TASK run_static_scrape no contacts found, escalating to dynamic scraper: %s", url)
        # Hand off to the JS-capable worker; that task saves its own results.
        run_dynamic_scrape.delay(url, campaign_id=campaign_id, source_id=source_id, proxy_url=proxy_url)
        return {"success": True, "processed": 0, "saved": 0,
                "note": "No contacts via static fetch; escalated to dynamic scraper."}

    return _process_and_save_scrape_result(result, campaign_id, source_id)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3, queue='playwright')
def run_dynamic_scrape(self, url: str, campaign_id: str = None, adspower_profile_id: str = None, proxy_url: str = None, source_id: str = None):
    """Executes a dynamic scrape explicitly on the isolated playwright_worker container."""
    logger.info("TASK run_dynamic_scrape START url=%s campaign=%s source=%s", url, campaign_id, source_id)
    source = LeadSource.objects.select_related('campaign').filter(id=source_id).first() if source_id else None
    campaign = _resolve_pipeline_campaign(campaign_id, source)
    if not _campaign_allows_pipeline_work(campaign, campaign_id, "run_dynamic_scrape"):
        return {"success": True, "processed": 0, "saved": 0, "skipped": "Campaign is not active."}

    scraper = DynamicScraper()
    result = scraper.scrape_website(url, adspower_profile_id=adspower_profile_id, proxy_url=proxy_url)
    return _process_and_save_scrape_result(result, campaign_id, source_id)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=2, queue='playwright')
def enrich_linkedin_lead_task(self, lead_id: str):
    """Open the lead's LinkedIn profile via AdsPower and enrich stored data.

    Runs on the playwright queue so it has access to the Playwright / Chrome runtime.
    Only executes when LINKEDIN_ENRICHMENT_ENABLED=true and ADSPOWER_PROFILE_ID is set.
    """
    if not getattr(settings, 'LINKEDIN_ENRICHMENT_ENABLED', False):
        return {'skipped': 'LINKEDIN_ENRICHMENT_ENABLED is false'}

    adspower_profile_id = getattr(settings, 'ADSPOWER_PROFILE_ID', '')
    adspower_api_url = getattr(settings, 'ADSPOWER_API_URL', 'http://host.docker.internal:50325')
    if not adspower_profile_id:
        return {'skipped': 'ADSPOWER_PROFILE_ID not configured'}

    lead = Lead.objects.filter(id=lead_id).first()
    if not lead:
        logger.warning("enrich_linkedin_lead_task: lead %s not found", lead_id)
        return {'error': 'lead not found'}

    linkedin_url = lead.linkedin_url or lead.profile_url
    if not linkedin_url or 'linkedin.com' not in linkedin_url:
        return {'skipped': 'no linkedin url on lead'}

    logger.info("TASK enrich_linkedin_lead START lead=%s url=%s", lead_id, linkedin_url)
    data = _scrape_linkedin_profile(
        linkedin_url=linkedin_url,
        adspower_profile_id=adspower_profile_id,
        adspower_api_url=adspower_api_url,
    )

    if not data.get('success'):
        logger.warning("TASK enrich_linkedin_lead FAILED lead=%s url=%s", lead_id, linkedin_url)
        return {'success': False}

    updated = False
    if data.get('first_name') and not lead.first_name:
        lead.first_name = data['first_name']
        updated = True
    if data.get('last_name') and not lead.last_name:
        lead.last_name = data['last_name']
        updated = True
    if data.get('title') and not lead.title:
        lead.title = data['title']
        updated = True
    if data.get('email') and not lead.email:
        # A real email was found on their LinkedIn — update the lead
        if not Lead.objects.filter(email=data['email']).exclude(id=lead.id).exists():
            lead.email = data['email']
            lead.is_generic_email = False
            updated = True
    if data.get('company') and not lead.company:
        # Try to match to an existing Company record by name
        company = Company.objects.filter(name__iexact=data['company']).first()
        if company:
            lead.company = company
            updated = True

    if updated:
        lead.save()
        logger.info(
            "TASK enrich_linkedin_lead ENRICHED lead=%s name=%s %s title=%s email=%s",
            lead_id, lead.first_name, lead.last_name, lead.title, lead.email,
        )
        log_activity(lead, 'linkedin_enriched',
                     f"LinkedIn profile enriched via AdsPower: {linkedin_url}",
                     {'linkedin_url': linkedin_url})
        # Re-score now that we have richer data
        score_lead_task.delay(lead_id)

    return {'success': True, 'updated': updated}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=2, queue='playwright')
def run_linkedin_source_scrape(self, source_id: str = None, campaign_id: str = None, keywords: str = None):
    """Search LinkedIn People for a query and save results as leads.

    Called two ways:
      1. From beat task — keywords derived from campaign.target_persona, no source_id.
      2. From a manual LinkedIn source in DB — source_id provided, keywords extracted from source.url.

    No LinkedIn entries in LeadSource are required — queries are auto-generated from
    campaign.target_persona when LINKEDIN_ENRICHMENT_ENABLED=true.
    """
    if not getattr(settings, 'LINKEDIN_ENRICHMENT_ENABLED', False):
        return {'skipped': 'LINKEDIN_ENRICHMENT_ENABLED is false'}

    adspower_profile_id = getattr(settings, 'ADSPOWER_PROFILE_ID', '')
    adspower_api_url = getattr(settings, 'ADSPOWER_API_URL', 'http://host.docker.internal:50325')
    if not adspower_profile_id:
        return {'skipped': 'ADSPOWER_PROFILE_ID not set'}

    source = LeadSource.objects.select_related('campaign').filter(id=source_id).first() if source_id else None
    campaign = _resolve_pipeline_campaign(campaign_id, source)
    if not _campaign_allows_pipeline_work(campaign, campaign_id, "run_linkedin_source_scrape"):
        return {'skipped': 'Campaign is not active.'}

    # Resolve keywords: explicit kwarg > source URL > empty
    if not keywords and source:
        url = source.url or ''
        if 'linkedin.com/search' in url:
            parsed = urllib.parse.urlparse(url)
            keywords = urllib.parse.parse_qs(parsed.query).get('keywords', [url])[0]
        else:
            keywords = url

    if not keywords:
        return {'skipped': 'no keywords provided'}

    logger.info("TASK run_linkedin_source_scrape START keywords=%r campaign=%s", keywords, campaign_id)

    people = search_and_scrape_linkedin(
        keywords=keywords,
        adspower_profile_id=adspower_profile_id,
        adspower_api_url=adspower_api_url,
        limit=30,
        enrich_profiles=False,  # fast pass — collect cards; full profiles enriched separately
    )

    if not _refresh_campaign_allows_pipeline_work(campaign, campaign_id, "run_linkedin_source_scrape save"):
        return {'skipped': 'Campaign is not active.', 'saved': 0}

    if not people:
        logger.info("TASK run_linkedin_source_scrape no people found for keywords=%r", keywords)
        if source:
            source.last_scraped_at = timezone.now()
            source.save(update_fields=['last_scraped_at'])
        return {'success': True, 'saved': 0}

    # Clean and save
    cleaned = DataCleaner(people).process()
    saved_count = 0
    for lead_data in cleaned:
        linkedin_url = lead_data.get('linkedin_url')
        profile_url = lead_data.get('profile_url') or linkedin_url
        if not linkedin_url and not profile_url:
            continue
        lead_name = ' '.join(
            part for part in [lead_data.get('first_name'), lead_data.get('last_name')]
            if part
        )
        if looks_like_clear_non_person_name(lead_name):
            logger.info("Skipped non-person LinkedIn lead name=%r campaign=%s", lead_name, campaign_id)
            continue

        lead = Lead.objects.filter(linkedin_url=linkedin_url).first() if linkedin_url else None
        if not lead and profile_url:
            lead = Lead.objects.filter(profile_url=profile_url).first()

        if not lead:
            # Try to infer company domain from keywords for company resolution
            page_company = None
            lead = Lead.objects.create(
                email=None,
                linkedin_url=linkedin_url,
                profile_url=profile_url,
                first_name=lead_data.get('first_name'),
                last_name=lead_data.get('last_name'),
                title=lead_data.get('title'),
                campaign=campaign,
                source=source,
                is_generic_email=False,
                status='uncontacted',
            )
            saved_count += 1
            logger.info("LEAD CREATED (linkedin) linkedin=%s title=%s campaign=%s",
                        linkedin_url, lead_data.get('title'), campaign_id)
            log_activity(lead, 'lead_created',
                         f"Found via LinkedIn search: {keywords}",
                         {'keywords': keywords, 'linkedin_url': linkedin_url})

            # Queue deep profile enrichment
            enrich_linkedin_lead_task.apply_async(
                args=[str(lead.id)],
                countdown=10,
                queue='playwright',
            )
            # Queue scoring after a delay (so enrichment can finish first)
            score_lead_task.apply_async(args=[str(lead.id)], countdown=90)
        else:
            # Update missing fields on existing lead
            updated = False
            if linkedin_url and not lead.linkedin_url:
                lead.linkedin_url = linkedin_url
                updated = True
            if lead_data.get('title') and not lead.title:
                lead.title = lead_data['title']
                updated = True
            if campaign and not lead.campaign:
                lead.campaign = campaign
                updated = True
            if source and not lead.source:
                lead.source = source
                updated = True
            if updated:
                lead.save()
                # Re-queue enrichment to pick up any updates
                enrich_linkedin_lead_task.apply_async(
                    args=[str(lead.id)], countdown=10, queue='playwright'
                )

    if source:
        source.last_scraped_at = timezone.now()
        source.save(update_fields=['last_scraped_at'])

    logger.info("TASK run_linkedin_source_scrape DONE keywords=%r saved=%d", keywords, saved_count)
    return {'success': True, 'saved': saved_count, 'found': len(people)}


def _linkedin_queries_for_campaign(campaign) -> list:
    """Auto-generate LinkedIn People search query strings from campaign.target_persona.

    No need to add LinkedIn sources manually — the system derives what to search
    for from the campaign's target_persona field.
    """
    persona = getattr(campaign, 'target_persona', '') or ''
    # Split comma-separated personas and build one query per persona
    personas = [p.strip() for p in persona.split(',') if p.strip()]
    if not personas:
        personas = ['english teacher trainer istanbul']

    queries = []
    geo_suffixes = ['istanbul', 'turkey', 'turkiye']
    for p in personas:
        # Base persona query
        queries.append(p)
        # Same persona + primary geo
        queries.append(f"{p} {geo_suffixes[0]}")
    # Add a few sector-specific catch-alls that work for any English-ed campaign
    queries.extend([
        'dil okulu muduru istanbul',
        'ingilizce dil kursu kurucu',
        'corporate english training manager turkey',
    ])
    return queries


@shared_task
def trigger_scheduled_scrapes_task():
    """Beat task: walks active campaigns and enqueues scrapes for their due LeadSources."""
    today = timezone.now().date()
    refresh_cutoff = timezone.now() - timezone.timedelta(hours=settings.SCRAPE_REFRESH_HOURS)
    linkedin_enabled = getattr(settings, 'LINKEDIN_ENRICHMENT_ENABLED', False)

    campaigns = Campaign.objects.filter(status='active')
    triggered = 0
    logger.info("BEAT trigger_scheduled_scrapes_task: checking %d active campaigns", campaigns.count())
    for campaign in campaigns:
        if campaign.start_date and campaign.start_date > today:
            logger.debug("Campaign %s not started yet, skipping", campaign.name)
            continue
        if campaign.end_date and campaign.end_date < today:
            logger.debug("Campaign %s ended, skipping", campaign.name)
            continue

        # ── Regular web sources (static / directory / dynamic) ──────────────
        all_sources = campaign.sources.exclude(source_type='linkedin').order_by('-priority_score')
        logger.info("Campaign %s has %d web sources", campaign.name, all_sources.count())

        for source in all_sources:
            if source.last_scraped_at and source.last_scraped_at > refresh_cutoff:
                logger.debug("Source %s recently scraped, skipping", source.url)
                continue
            source.last_scraped_at = timezone.now()
            source.save(update_fields=['last_scraped_at'])

            if source.source_type == 'dynamic':
                run_dynamic_scrape.delay(source.url, campaign_id=str(campaign.id), source_id=str(source.id))
            else:
                run_static_scrape.delay(source.url, campaign_id=str(campaign.id), source_id=str(source.id))
            triggered += 1
            logger.info("QUEUED scrape for %s (campaign: %s)", source.url, campaign.name)

        # ── LinkedIn auto-search from campaign.target_persona ────────────────
        # No LinkedIn sources needed in DB — queries are derived automatically.
        if linkedin_enabled:
            for query in _linkedin_queries_for_campaign(campaign):
                run_linkedin_source_scrape.apply_async(
                    kwargs={'source_id': None, 'campaign_id': str(campaign.id), 'keywords': query},
                    queue='playwright',
                )
                triggered += 1
                logger.info("QUEUED linkedin search %r (campaign: %s)", query, campaign.name)

    logger.info("BEAT trigger_scheduled_scrapes_task: triggered %d scrapes", triggered)
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

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=2)
def enrich_lead_email_task(self, lead_id: str):
    """Find a real email address for a named lead that has no email yet.

    Lookup order (no additional API accounts required beyond what is already
    configured — we reuse the Serper search API that powers lead discovery):

      1. Serper-based email search — runs targeted Google searches for the
         person's name + company domain and scans snippets + on-domain pages.
         Free Serper tier gives 2,500 searches/month; paid plans are unlimited.
      2. Hunter.io email-finder — optional, requires HUNTER_API_KEY in .env.
         Free tier is only 25/month so not the primary strategy.
      3. Pattern inference — firstname.lastname@domain fallback.  Never wrong
         for companies that use the first.last convention (the majority).
         Guessed addresses that bounce are auto-suppressed by the IMAP handler.

    When an email is found the lead is updated, an activity is logged, and
    generate_draft_task is queued if the lead score is already above threshold.
    """
    lead = Lead.objects.filter(id=lead_id).first()
    if not lead:
        return "Lead not found"
    if lead.email:
        return "Lead already has email"
    if not (lead.first_name and lead.last_name):
        return "Lead has no full name — cannot search or infer email"
    lead_name = ' '.join(filter(None, [lead.first_name, lead.last_name]))
    if looks_like_clear_non_person_name(lead_name):
        return "Lead name is not a person — skip email enrichment"

    # Resolve the company domain
    domain = None
    if lead.company and lead.company.domain:
        domain = lead.company.domain.lower().lstrip('www.')
    if not domain and lead.profile_url:
        from urllib.parse import urlparse
        parsed = urlparse(lead.profile_url)
        if parsed.netloc and 'linkedin' not in parsed.netloc:
            domain = parsed.netloc.lstrip('www.')
    if not domain:
        return "No company domain — cannot enrich email"

    if domain in FREE_EMAIL_PROVIDERS:
        return f"Free email provider ({domain}) — skip"

    email = None
    method = None

    # --- Step 1: Serper-based search (reuses existing API key, no extra cost) ---
    try:
        from scraper.search import search_person_email as _serper_find
        email = _serper_find(lead.first_name, lead.last_name, domain)
        if email:
            method = "serper-search"
    except Exception as exc:
        logger.warning("enrich_lead_email_task serper search error: %s", exc)

    # --- Step 2: Hunter.io (optional, requires HUNTER_API_KEY) ---
    if not email:
        hunter_key = getattr(settings, 'HUNTER_API_KEY', '') or None
        if hunter_key:
            try:
                from scraper.hunter import find_email as hunter_find
                result = hunter_find(lead.first_name, lead.last_name, domain, hunter_key)
                if result and result.get('email'):
                    email = result['email']
                    method = "hunter-io"
            except Exception as exc:
                logger.warning("enrich_lead_email_task hunter error: %s", exc)

    # --- Step 3: Pattern inference (always runs as last fallback) ---
    if not email:
        try:
            from scraper.hunter import infer_email
            email = infer_email(lead.first_name, lead.last_name, domain, api_key=None)
            if email:
                method = "pattern-inference"
        except Exception as exc:
            logger.warning("enrich_lead_email_task inference error: %s", exc)

    if not email:
        return "Could not find or infer email"

    # Prevent collision with an existing lead
    if Lead.objects.filter(email=email).exclude(id=lead.id).exists():
        logger.info("enrich_lead_email: %s already belongs to another lead", email)
        return f"Email {email} already exists on another lead"

    lead.email = email
    lead.save(update_fields=['email'])
    log_activity(lead, 'email_enriched', f"Email found via {method}: {email}")
    logger.info("TASK enrich_lead_email DONE lead=%s email=%s method=%s", lead_id, email, method)

    # If score is already above threshold and campaign is active, queue draft now
    campaign = lead.campaign
    if (lead.lead_score and lead.lead_score >= settings.LEAD_SCORE_THRESHOLD
            and campaign and campaign.status == 'active'
            and campaign.outreach_channel != 'linkedin'):
        generate_draft_task.delay(str(lead.id))

    return f"Email enriched via {method}: {email}"


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def score_lead_task(self, lead_id: str):
    """Uses LLM to score a lead, assign a persona, match a lead magnet, and recommend an angle."""
    logger.info("TASK score_lead_task START lead=%s", lead_id)
    lead = Lead.objects.filter(id=lead_id).first()
    if not lead:
        logger.warning("TASK score_lead_task lead not found: %s", lead_id)
        return "Lead not found"

    campaign_persona = lead.campaign.target_persona if lead.campaign else "Any B2B prospect"
    company_vp = lead.company.value_proposition if lead.company else None

    magnets = list(LeadMagnet.objects.all().values('name', 'description', 'target_persona'))

    lead_name = ' '.join(filter(None, [lead.first_name, lead.last_name])) or None

    score_data = score_lead(
        lead_title=lead.title,
        company_vp=company_vp,
        campaign_persona=campaign_persona,
        available_lead_magnets=magnets,
        is_generic_email=lead.is_generic_email,
        company_name=lead.company.name if lead.company else None,
        lead_name=lead_name,
    )

    if score_data:
        lead.lead_score, lead.score_reason = _normalize_lead_score(lead, score_data)
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

    logger.info("TASK score_lead_task DONE lead=%s score=%s", lead_id, lead.lead_score)
    return f"Scored lead {lead.email or lead.linkedin_url} with score {lead.lead_score}"

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def generate_draft_task(self, lead_id: str):
    """Uses LLM to draft a personalized email and saves it to the database."""
    logger.info("TASK generate_draft_task START lead=%s", lead_id)
    lead = Lead.objects.filter(id=lead_id).first()
    if not lead or not lead.campaign:
        logger.warning("TASK generate_draft_task lead/campaign not found: %s", lead_id)
        return "Lead or campaign not found"

    if lead.campaign.status != 'active':
        logger.info(
            "TASK generate_draft_task skipped lead=%s campaign=%s status=%s",
            lead_id, lead.campaign_id, lead.campaign.status,
        )
        return "Campaign is not active"

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

        logger.info("TASK generate_draft_task DONE lead=%s status=%s", lead_id, status)
        return f"Drafted email for {lead.email}"
    logger.error("TASK generate_draft_task FAILED to generate draft for lead=%s", lead_id)
    return "Failed to draft email"

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def generate_linkedin_task_task(self, lead_id: str):
    """Creates a manual LinkedIn 'connect' task with an AI-drafted connection note (SRS 3.14)."""
    lead = Lead.objects.filter(id=lead_id).first()
    if not lead or not lead.campaign:
        return "Lead or campaign not found"

    if lead.campaign.status != 'active':
        return "Campaign is not active"

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

    if lead.campaign.status != 'active':
        return "Campaign is not active"

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
