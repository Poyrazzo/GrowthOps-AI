import urllib.parse
from celery import shared_task
from scraper.static import StaticScraper
from scraper.dynamic import DynamicScraper
from scraper.cleaner import DataCleaner
from crm.models import Lead, Campaign, Company, Message
from ai_engine.company_profiler import extract_company_info
from ai_engine.lead_profiler import score_lead
from ai_engine.email_generator import generate_email_draft

def _process_and_save_scrape_result(result: dict, campaign_id: str = None) -> dict:
    """Fans out the raw scraper result, cleans it, and saves it to the DB."""
    if not result.get('success'):
        return {"success": False, "error": "Scrape failed or returned empty HTML.", "processed": 0, "saved": 0}
        
    url = result.get('url', '')
    domain = urllib.parse.urlparse(url).netloc
    if domain.startswith('www.'):
        domain = domain[4:]
        
    company = None
    if domain:
        company, _ = Company.objects.get_or_create(domain=domain, defaults={'name': domain})
        
    raw_leads = []
    emails = result.get('emails', [])
    social_links = result.get('social_links', {})
    
    # Fan out by email
    for email in emails:
        raw_leads.append({
            'email': email,
            'linkedin_url': social_links.get('linkedin') # attach linkedin if found on same page
        })
        
    # If no emails, but a linkedin exists
    if not raw_leads and social_links.get('linkedin'):
        raw_leads.append({
            'email': None,
            'linkedin_url': social_links.get('linkedin')
        })
        
    cleaner = DataCleaner(raw_leads)
    cleaned_leads = cleaner.process()
    
    saved_count = 0
    campaign = None
    if campaign_id:
        campaign = Campaign.objects.filter(id=campaign_id).first()
        
    for lead_data in cleaned_leads:
        email = lead_data.get('email')
        linkedin_url = lead_data.get('linkedin_url')
        
        # DataCleaner guarantees at least one exists, but let's be absolutely safe
        if not email and not linkedin_url:
            continue
            
        lead = None
        if email:
            lead = Lead.objects.filter(email=email).first()
        if not lead and linkedin_url:
            lead = Lead.objects.filter(linkedin_url=linkedin_url).first()
            
        created = False
        if not lead:
            lead = Lead.objects.create(
                email=email,
                linkedin_url=linkedin_url,
                first_name=lead_data.get('first_name'),
                last_name=lead_data.get('last_name'),
                campaign=campaign,
                company=company,
                status='uncontacted'
            )
            created = True
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
                
        if created:
            saved_count += 1
            
    body_text = result.get('body_text', '')
    if company:
        enrich_company_task.delay(str(company.id), body_text)
            
    return {
        "success": True,
        "processed": len(cleaned_leads),
        "saved": saved_count,
        "campaign_id": campaign_id
    }

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def run_static_scrape(self, url: str, campaign_id: str = None, proxy_url: str = None):
    """Executes a static scrape in the background on the default Celery queue."""
    scraper = StaticScraper()
    result = scraper.scrape_website(url, proxy_url=proxy_url)
    return _process_and_save_scrape_result(result, campaign_id)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3, queue='playwright')
def run_dynamic_scrape(self, url: str, campaign_id: str = None, adspower_profile_id: str = None, proxy_url: str = None):
    """Executes a dynamic scrape explicitly on the isolated playwright_worker container."""
    scraper = DynamicScraper()
    result = scraper.scrape_website(url, adspower_profile_id=adspower_profile_id, proxy_url=proxy_url)
    return _process_and_save_scrape_result(result, campaign_id)

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
    """Uses LLM to score a lead and recommend a messaging angle."""
    lead = Lead.objects.filter(id=lead_id).first()
    if not lead or not lead.company:
        return "Lead or company not found"
        
    campaign_persona = lead.campaign.target_persona if lead.campaign else "Any B2B prospect"
    
    score_data = score_lead(
        lead_title=lead.title,
        company_vp=lead.company.value_proposition,
        campaign_persona=campaign_persona
    )
    
    if score_data:
        lead.lead_score = score_data.get('score', 0)
        lead.score_reason = score_data.get('reasoning', '')
        lead.recommended_message_angle = score_data.get('recommended_message_angle', '')
        lead.save()
        
        if lead.lead_score >= 50:
            generate_draft_task.delay(str(lead.id))
        
    return f"Scored lead {lead.email or lead.linkedin_url} with score {lead.lead_score}"

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def generate_draft_task(self, lead_id: str):
    """Uses LLM to draft a personalized email and saves it to the database."""
    lead = Lead.objects.filter(id=lead_id).first()
    if not lead or not lead.campaign:
        return "Lead or campaign not found"
        
    if Message.objects.filter(lead=lead, status='pending').exists():
        return "Draft already exists for this lead"
        
    company_name = lead.company.name if lead.company else "Unknown"
    company_vp = lead.company.value_proposition if lead.company else "Unknown"
    lead_magnet_desc = lead.campaign.lead_magnet or "None"
    
    draft_data = generate_email_draft(
        lead_name=lead.first_name,
        lead_title=lead.title,
        company_name=company_name,
        company_vp=company_vp,
        campaign_vp=lead.campaign.value_proposition,
        message_angle=lead.recommended_message_angle,
        lead_magnet=lead_magnet_desc
    )
    
    if draft_data and draft_data.get('subject') and draft_data.get('body'):
        Message.objects.create(
            lead=lead,
            campaign=lead.campaign,
            channel='email',
            subject=draft_data['subject'],
            body=draft_data['body'],
            status='pending'
        )
        return f"Drafted email for {lead.email}"
    return "Failed to draft email"
