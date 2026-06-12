import logging
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError
from typing import Dict, Any, Optional
from .static import StaticScraper
from .extractor import extract_contacts, find_contact_links, extract_social_links
from .adspower import AdsPowerManager

logger = logging.getLogger(__name__)


class DynamicScraper:
    """Fetches JS-rendered pages with Playwright and extracts contacts."""

    def __init__(self, timeout_ms: int = 15000):
        self.timeout_ms = timeout_ms

    def fetch_html(self, url: str, adspower_profile_id: Optional[str] = None, proxy_url: Optional[str] = None) -> str | None:
        """Launches a headless browser (or connects to AdsPower), waits for network idle, returns HTML."""
        if not url.startswith('http'):
            url = 'https://' + url

        html = None
        ws_endpoint = None
        ads_manager = None

        try:
            if adspower_profile_id:
                ads_manager = AdsPowerManager()
                ws_endpoint = ads_manager.start_profile(adspower_profile_id)

            with sync_playwright() as p:
                if ws_endpoint:
                    browser = p.chromium.connect_over_cdp(ws_endpoint)
                    context = browser.contexts[0] if browser.contexts else browser.new_context(ignore_https_errors=True)
                else:
                    launch_args = {'headless': True}
                    if proxy_url:
                        launch_args['proxy'] = {'server': proxy_url}
                    browser = p.chromium.launch(**launch_args)
                    context = browser.new_context(ignore_https_errors=True)

                page = context.pages[0] if context.pages else context.new_page()

                page.goto(url, wait_until='networkidle', timeout=self.timeout_ms)
                html = page.content()
                logger.debug("Playwright fetched %s (%d chars)", url, len(html))
                browser.close()
        except TimeoutError:
            logger.warning("Playwright timeout fetching %s", url)
        except Exception as e:
            logger.warning("Playwright error fetching %s: %s", url, e)
        finally:
            if adspower_profile_id and ads_manager:
                try:
                    ads_manager.stop_profile(adspower_profile_id)
                except Exception as e:
                    logger.error("Failed to stop AdsPower profile %s: %s", adspower_profile_id, e)

        return html

    def scrape_website(self, url: str, adspower_profile_id: Optional[str] = None, proxy_url: Optional[str] = None) -> Dict[str, Any]:
        """Render the page with a real browser, extract contacts, and crawl contact sub-pages."""
        logger.info("DynamicScraper starting: %s", url)
        result = {
            'url': url, 'success': False, 'metadata': {}, 'body_text': '',
            'emails': [], 'contacts': [], 'social_links': {}
        }

        html = self.fetch_html(url, adspower_profile_id, proxy_url)
        if not html:
            logger.warning("DynamicScraper got no HTML for %s", url)
            return result

        static_parser = StaticScraper()
        soup = BeautifulSoup(html, 'html.parser')
        result['metadata'] = static_parser.extract_metadata(soup)
        result['body_text'] = static_parser.extract_visible_text(soup)

        contacts_by_email: Dict[str, Any] = {}
        socials = extract_social_links(soup)

        def _merge(contacts):
            for c in contacts:
                cur = contacts_by_email.get(c['email'])
                if cur is None:
                    contacts_by_email[c['email']] = c
                else:
                    cur['first_name'] = cur['first_name'] or c['first_name']
                    cur['last_name'] = cur['last_name'] or c['last_name']

        _merge(extract_contacts(soup, html))

        # Render contact/about sub-pages too (JS sites often hide emails there).
        for link in find_contact_links(soup, url, limit=3):
            logger.debug("DynamicScraper crawling sub-page: %s", link)
            sub_html = self.fetch_html(link, adspower_profile_id, proxy_url)
            if not sub_html:
                continue
            sub_soup = BeautifulSoup(sub_html, 'html.parser')
            _merge(extract_contacts(sub_soup, sub_html))
            for p in extract_social_links(sub_soup).get('linkedin_profiles', []):
                socials['linkedin_profiles'].append(p)

        contacts = list(contacts_by_email.values())
        result['contacts'] = contacts
        result['emails'] = [c['email'] for c in contacts]
        result['social_links'] = socials
        result['success'] = True
        logger.info("DynamicScraper done %s — %d contacts found", url, len(contacts))
        return result
