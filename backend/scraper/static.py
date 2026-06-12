import re
import logging
import urllib.parse
import requests
import urllib3
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List, Tuple

from .extractor import (
    extract_contacts, find_listing_links,
    extract_social_links, common_person_page_links,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# Path fragments that signal a high-value contact/people page — visited first.
_PRIORITY_PATH_HINTS = (
    'ekip', 'kadro', 'personel', 'ogretmen', 'öğretmen', 'egitmen', 'eğitmen',
    'hoca', 'akademik', 'faculty', 'team', 'staff', 'people', 'members',
    'teacher', 'trainer', 'instructor', 'consultant', 'expert', 'uzman',
    'hakkimizda', 'hakkında', 'about', 'iletisim', 'contact', 'kurumsal',
    'yonetim', 'yönetim', 'leadership', 'management', 'board', 'advisors',
)

_SKIP_EXTENSIONS = (
    '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg',
    '.js', '.css', '.zip', '.ico', '.woff', '.woff2', '.xml',
    '.txt', '.mp4', '.mp3', '.avi', '.doc', '.docx', '.xls',
)


class StaticScraper:
    """Full-site BFS crawler that extracts contacts from every reachable page
    on the same domain. Starts from the given URL, follows all internal links,
    and prioritises contact/team/staff pages."""

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    # Max pages to visit per source (BFS). Each page costs ~1-10 s.
    MAX_CRAWL_PAGES = 80
    # For directory sources: how many individual listing pages to crawl into.
    MAX_LISTING_PAGES = 20

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def fetch_html(self, url: str, proxy_url: Optional[str] = None) -> Optional[str]:
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
                logger.warning("Error fetching %s (SSL fallback): %s", url, e)
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

    # Backward-compatible helpers
    def extract_emails(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, 'html.parser')
        return [c['email'] for c in extract_contacts(soup, html) if c.get('email')]

    def extract_social_links(self, soup: BeautifulSoup) -> Dict[str, Any]:
        return extract_social_links(soup)

    def _is_priority(self, url: str) -> bool:
        path = urllib.parse.urlparse(url).path.lower()
        return any(hint in path for hint in _PRIORITY_PATH_HINTS)

    def _crawl_site(
        self, start_url: str, proxy_url: Optional[str] = None
    ) -> List[Tuple[str, BeautifulSoup, str]]:
        """BFS-crawl the whole site. Returns list of (url, soup, html) for every
        successfully fetched page, up to MAX_CRAWL_PAGES."""
        parsed_start = urllib.parse.urlparse(
            start_url if start_url.startswith('http') else f'https://{start_url}'
        )
        base_host = parsed_start.netloc.lower()

        visited: set = set()
        results: List[Tuple[str, BeautifulSoup, str]] = []

        # Two queues: priority (team/contact pages) and normal.
        priority_queue: List[str] = []
        normal_queue: List[str] = []
        queued: set = set()

        def _enqueue(url: str) -> None:
            clean = url.split('#', 1)[0].rstrip('/')
            if not clean or clean in queued:
                return
            queued.add(clean)
            if self._is_priority(clean):
                priority_queue.insert(0, clean)
            else:
                normal_queue.append(clean)

        _enqueue(start_url)

        # Pre-queue guessed staff paths (Turkish + English) so we always try them
        for guessed in common_person_page_links(start_url, limit=30):
            _enqueue(guessed)

        while len(results) < self.MAX_CRAWL_PAGES:
            # Always drain priority queue first
            if priority_queue:
                url = priority_queue.pop(0)
            elif normal_queue:
                url = normal_queue.pop(0)
            else:
                break

            if url in visited:
                continue
            visited.add(url)

            html = self.fetch_html(url, proxy_url=proxy_url)
            if not html:
                continue

            soup = BeautifulSoup(html, 'html.parser')
            results.append((url, soup, html))
            logger.debug("StaticScraper crawled (%d/%d): %s",
                         len(results), self.MAX_CRAWL_PAGES, url)

            # Discover all internal links from this page
            for a in soup.find_all('a', href=True):
                href = a['href'].strip()
                if not href or href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
                    continue
                absolute = urllib.parse.urljoin(url, href)
                parsed = urllib.parse.urlparse(absolute)
                if parsed.netloc.lower() != base_host:
                    continue
                path = parsed.path.lower()
                if any(path.endswith(ext) for ext in _SKIP_EXTENSIONS):
                    continue
                _enqueue(absolute)

        logger.info("StaticScraper BFS done %s — %d pages crawled", start_url, len(results))
        return results

    def scrape_website(self, url: str, proxy_url: Optional[str] = None,
                       is_directory: bool = False) -> Dict[str, Any]:
        logger.info("StaticScraper starting: %s (directory=%s)", url, is_directory)
        result = {
            'url': url, 'success': False, 'metadata': {}, 'body_text': '',
            'emails': [], 'contacts': [], 'social_links': {}
        }

        pages = self._crawl_site(url, proxy_url=proxy_url)
        if not pages:
            logger.warning("StaticScraper got no HTML for %s", url)
            return result

        contacts_by_key: Dict[str, Dict[str, Any]] = {}
        socials: Dict[str, Any] = {'linkedin_company': None, 'linkedin_profiles': []}

        def _merge(contacts):
            for c in contacts:
                email = c.get('email')
                linkedin_url = c.get('linkedin_url')
                profile_url = c.get('profile_url')
                if not email and not linkedin_url and not profile_url:
                    continue
                if email:
                    key = f"email:{email}"
                elif linkedin_url:
                    key = f"linkedin:{linkedin_url.lower().rstrip('/')}"
                else:
                    key = f"profile:{(c.get('first_name') or '')}_{(c.get('last_name') or '')}@{profile_url.rstrip('/')}"
                cur = contacts_by_key.get(key)
                if cur is None:
                    contacts_by_key[key] = dict(c)
                else:
                    cur['linkedin_url'] = cur.get('linkedin_url') or linkedin_url
                    cur['profile_url'] = cur.get('profile_url') or profile_url
                    cur['first_name'] = cur.get('first_name') or c.get('first_name')
                    cur['last_name'] = cur.get('last_name') or c.get('last_name')
                    cur['title'] = cur.get('title') or c.get('title')

        first_page = True
        for page_url, soup, html in pages:
            if first_page:
                result['metadata'] = self.extract_metadata(soup)
                result['body_text'] = self.extract_visible_text(soup)
                first_page = False
            _merge(extract_contacts(soup, html, source_url=page_url))
            sub_socials = extract_social_links(soup)
            if sub_socials.get('linkedin_company') and not socials.get('linkedin_company'):
                socials['linkedin_company'] = sub_socials['linkedin_company']
            for p in sub_socials.get('linkedin_profiles', []):
                if p not in socials['linkedin_profiles']:
                    socials['linkedin_profiles'].append(p)

        # For directory sources: follow individual listing links inside each listing page.
        if is_directory and pages:
            first_soup = pages[0][1]
            listing_links = find_listing_links(first_soup, url, limit=self.MAX_LISTING_PAGES)
            logger.info("StaticScraper directory mode: %d listing links in %s",
                        len(listing_links), url)
            for link in listing_links:
                lst_html = self.fetch_html(link, proxy_url=proxy_url)
                if not lst_html:
                    continue
                lst_soup = BeautifulSoup(lst_html, 'html.parser')
                _merge(extract_contacts(lst_soup, lst_html, source_url=link))

        contacts = list(contacts_by_key.values())
        result['contacts'] = contacts
        result['emails'] = [c['email'] for c in contacts if c.get('email')]
        result['social_links'] = socials
        result['success'] = True
        logger.info("StaticScraper done %s — %d pages, %d contacts",
                    url, len(pages), len(contacts))
        return result
