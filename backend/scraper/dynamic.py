from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError
from typing import Dict, Any, Optional
from .static import StaticScraper
from .adspower import AdsPowerManager

class DynamicScraper:
    """
    Utility class for fetching and parsing dynamic HTML content from websites using Playwright.
    """

    def __init__(self, timeout_ms: int = 15000):
        self.timeout_ms = timeout_ms

    def fetch_html(self, url: str, adspower_profile_id: Optional[str] = None, proxy_url: Optional[str] = None) -> str | None:
        """Launches a headless browser or connects to AdsPower, waits for network idle, and returns HTML."""
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
                else:
                    launch_args = {'headless': True}
                    if proxy_url:
                        launch_args['proxy'] = {'server': proxy_url}
                    browser = p.chromium.launch(**launch_args)
                
                # If connecting via CDP to AdsPower, a context/page usually already exists
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                page = context.pages[0] if context.pages else context.new_page()

                # Wait until there are no more than 0 network connections for at least 500 ms.
                page.goto(url, wait_until='networkidle', timeout=self.timeout_ms)
                html = page.content()
                browser.close()
        except TimeoutError:
            print(f"Playwright timeout fetching {url}")
        except Exception as e:
            print(f"Playwright error fetching {url}: {e}")
        finally:
            if adspower_profile_id and ads_manager:
                try:
                    ads_manager.stop_profile(adspower_profile_id)
                except Exception as e:
                    print(f"Failed to stop AdsPower profile {adspower_profile_id}: {e}")

        return html

    def scrape_website(self, url: str, adspower_profile_id: Optional[str] = None, proxy_url: Optional[str] = None) -> Dict[str, Any]:
        """Orchestrates dynamic fetching and uses StaticScraper's parsing logic."""
        result = {
            'url': url,
            'success': False,
            'metadata': {},
            'body_text': '',
            'emails': [],
            'social_links': {}
        }

        html = self.fetch_html(url, adspower_profile_id, proxy_url)
        if not html:
            return result

        # Re-use the StaticScraper for identical parsing logic
        static_parser = StaticScraper()
        soup = BeautifulSoup(html, 'html.parser')
        
        result['metadata'] = static_parser.extract_metadata(soup)
        result['body_text'] = static_parser.extract_visible_text(soup)
        result['emails'] = static_parser.extract_emails(html)
        result['social_links'] = static_parser.extract_social_links(soup)
        result['success'] = True

        return result
