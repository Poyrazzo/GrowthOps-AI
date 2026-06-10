from celery import shared_task
from scraper.static import StaticScraper
from scraper.dynamic import DynamicScraper
from scraper.cleaner import DataCleaner
from crm.models import Lead, Campaign

def _process_and_save_scrape_result(result: dict, campaign_id: str = None) -> dict:
    """Fans out the raw scraper result, cleans it, and saves it to the DB."""
    if not result.get('success'):
        return {"success": False, "error": "Scrape failed or returned empty HTML.", "processed": 0, "saved": 0}
        
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
            
        lead, created = Lead.objects.get_or_create(
            email=email,
            linkedin_url=linkedin_url,
            defaults={
                'first_name': lead_data.get('first_name'),
                'last_name': lead_data.get('last_name'),
                'campaign': campaign,
                'status': 'uncontacted'
            }
        )
        if created:
            saved_count += 1
            
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
