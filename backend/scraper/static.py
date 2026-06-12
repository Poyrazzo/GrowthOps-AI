import re
import logging
import requests
import urllib3
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List

from .extractor import extract_contacts, find_contact_links, extract_social_links

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class StaticScraper:
    """Fetches static HTML and extracts contacts. Beyond a single page, it discovers
    and crawls a few contact/about/team sub-pages where emails usually live."""

    # A realistic browser header set; some sites 403 bare python-requests.
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    # How many contact sub-pages to follow per site.
    MAX_SUBPAGES = 4

    def __init__(self, timeout: int = 12):
        self.timeout = timeout

    def fetch_html(self, url: str, proxy_url: Optional[str] = None) -> Optional[str]:
        """Fetch raw HTML, retrying once without TLS verification for broken cert chains."""
        if not url.startswith('http'):
            url = 'https://' + url
        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

        try:
            r = requests.get(url, headers=self.HEADERS, timeout=self.timeout, proxies=proxies)
            r.raise_for_status()
            return r.text
        except requests.exceptions.SSLError:
            try:
                r = requests.get(url, headers=self.HEADERS, timeout=self.timeout,
                                 proxies=proxies, verify=False)
                r.raise_for_status()
                return r.text
            except requests.RequestException as e:
                logger.warning("Error fetching %s (SSL fallback failed): %s", url, e)
                return None
        except requests.RequestException as e:
            logger.warning("Error fetching %s: %s", url, e)
            return None

    def extract_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        metadata = {'title': '', 'description': ''}
        if soup.title and soup.title.string:
            metadata['title'] = soup.title.string.strip()
        meta_desc = soup.find('meta', attrs={'name': 'description'}) or \
            soup.find('meta', attrs={'property': 'og:description'})
        if meta_desc and meta_desc.get('content'):
            metadata['description'] = meta_desc['content'].strip()
        return metadata

    def extract_visible_text(self, soup: BeautifulSoup) -> str:
        for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            element.decompose()
        text = soup.get_text(separator=' ', strip=True)
        return re.sub(r'\s+', ' ', text)

    # Backward-compatible helpers (other code/tests may still call these)
    def extract_emails(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, 'html.parser')
        return [c['email'] for c in extract_contacts(soup, html)]

    def extract_social_links(self, soup: BeautifulSoup) -> Dict[str, Any]:
        return extract_social_links(soup)

    def scrape_website(self, url: str, proxy_url: Optional[str] = None) -> Dict[str, Any]:
        """Fetch the landing page, then crawl a few contact/about/team sub-pages,
        aggregating contacts (with names) and social links across all of them."""
        logger.info("StaticScraper starting: %s", url)
        result = {
            'url': url, 'success': False, 'metadata': {}, 'body_text': '',
            'emails': [], 'contacts': [], 'social_links': {}
        }

        html = self.fetch_html(url, proxy_url=proxy_url)
        if not html:
            logger.warning("StaticScraper got no HTML for %s", url)
            return result

        soup = BeautifulSoup(html, 'html.parser')
        result['metadata'] = self.extract_metadata(soup)
        result['body_text'] = self.extract_visible_text(soup)

        contacts_by_email: Dict[str, Dict[str, Any]] = {}
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

        # Crawl contact/about/team sub-pages for more (and better) contacts.
        for link in find_contact_links(soup, url, limit=self.MAX_SUBPAGES):
            sub_html = self.fetch_html(link, proxy_url=proxy_url)
            if not sub_html:
                continue
            sub_soup = BeautifulSoup(sub_html, 'html.parser')
            _merge(extract_contacts(sub_soup, sub_html))
            sub_socials = extract_social_links(sub_soup)
            socials.setdefault('linkedin_company', sub_socials.get('linkedin_company'))
            for p in sub_socials.get('linkedin_profiles', []):
                socials['linkedin_profiles'].append(p)

        contacts = list(contacts_by_email.values())
        result['contacts'] = contacts
        result['emails'] = [c['email'] for c in contacts]
        result['social_links'] = socials
        result['success'] = True
        logger.info("StaticScraper done %s — %d contacts found", url, len(contacts))
        return result
