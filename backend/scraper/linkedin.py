"""LinkedIn scraping via AdsPower (real browser + persistent logged-in session).

Architecture
------------
AdsPowerManager.start_profile() launches the real Chrome profile that has LinkedIn
session cookies — no manual login needed each time. The playwright CDP connection
then drives that same browser. stop_profile() closes it when done.

LinkedInScraper wraps one AdsPower session for the lifetime of a task:
  - search_people(keywords, limit)   — browse LinkedIn people search, collect cards
  - scrape_profile(url)              — visit one profile, extract structured data

Both operations share one browser open/close cycle for efficiency.
"""
import logging
import re
import time
import urllib.parse
from typing import Any, Dict, List, Optional

from playwright.sync_api import Browser, Page, sync_playwright, TimeoutError as PlaywrightTimeout

from .adspower import AdsPowerManager

logger = logging.getLogger(__name__)

_NOISE_RE = re.compile(
    r'\b(connect|follow|message|send inmail|more|save|share|report|block|'
    r'mutual connection|mutual connections|you and)\b',
    re.I,
)


def _clean(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    text = ' '.join(text.split())
    return text or None


def _extract_li_profile_url(href: str) -> Optional[str]:
    """Normalize a LinkedIn profile href to a canonical URL."""
    if not href:
        return None
    # Strip tracking params (?miniProfile=..., ?trk=..., etc.)
    parsed = urllib.parse.urlparse(href)
    if '/in/' not in parsed.path:
        return None
    clean = f"https://www.linkedin.com{parsed.path.rstrip('/')}"
    return clean


class LinkedInScraper:
    """One AdsPower browser session that can search and scrape LinkedIn."""

    def __init__(
        self,
        adspower_profile_id: str,
        adspower_api_url: str = 'http://host.docker.internal:50325',
        timeout_ms: int = 20000,
    ):
        self.profile_id = adspower_profile_id
        self.timeout_ms = timeout_ms
        self._ads = AdsPowerManager()
        self._ads.api_url = adspower_api_url
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._ws_endpoint: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Session lifecycle                                                    #
    # ------------------------------------------------------------------ #

    def open(self) -> bool:
        """Start AdsPower profile and connect Playwright. Returns True on success."""
        try:
            self._ws_endpoint = self._ads.start_profile(self.profile_id)
            logger.info("AdsPower profile %s started", self.profile_id)
        except Exception as exc:
            logger.error("AdsPower start_profile failed: %s", exc)
            return False

        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.connect_over_cdp(self._ws_endpoint)
            ctx = self._browser.contexts[0] if self._browser.contexts else self._browser.new_context(ignore_https_errors=True)
            self._page = ctx.pages[0] if ctx.pages else ctx.new_page()
            logger.info("Playwright connected to AdsPower browser")
            return True
        except Exception as exc:
            logger.error("Playwright CDP connection failed: %s", exc)
            self.close()
            return False

    def close(self):
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        try:
            self._ads.stop_profile(self.profile_id)
            logger.info("AdsPower profile %s stopped", self.profile_id)
        except Exception as exc:
            logger.warning("stop_profile failed: %s", exc)
        self._browser = None
        self._playwright = None
        self._page = None

    def _goto(self, url: str, wait: str = 'domcontentloaded') -> bool:
        try:
            self._page.goto(url, wait_until=wait, timeout=self._timeout_ms)
            self._page.wait_for_timeout(2500)
            return True
        except PlaywrightTimeout:
            logger.warning("Timeout navigating to %s", url)
            return False

    @property
    def _timeout_ms(self):
        return self.timeout_ms

    def _is_auth_wall(self) -> bool:
        url = self._page.url
        return any(k in url for k in ('authwall', '/login', '/signup', '/uas/'))

    # ------------------------------------------------------------------ #
    # LinkedIn People Search                                               #
    # ------------------------------------------------------------------ #

    def search_people(self, keywords: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Search LinkedIn people by keywords. Returns list of person dicts."""
        search_url = (
            'https://www.linkedin.com/search/results/people/'
            f'?keywords={urllib.parse.quote(keywords)}'
            '&origin=GLOBAL_SEARCH_HEADER'
        )
        logger.info("LinkedIn search: %r limit=%d", keywords, limit)

        if not self._goto(search_url):
            return []
        if self._is_auth_wall():
            logger.warning("Auth wall on LinkedIn search — session expired? keywords=%r", keywords)
            return []

        people: List[Dict[str, Any]] = []
        seen: set = set()
        page_num = 0

        while len(people) < limit:
            page_num += 1
            cards = self._page.query_selector_all('li.reusable-search__result-container')
            if not cards:
                # Fallback selector
                cards = self._page.query_selector_all('li[class*="result-container"]')
            if not cards:
                logger.debug("No result cards found on page %d", page_num)
                break

            for card in cards:
                if len(people) >= limit:
                    break

                # Profile URL
                link_el = card.query_selector('a[href*="/in/"]')
                if not link_el:
                    continue
                href = link_el.get_attribute('href') or ''
                profile_url = _extract_li_profile_url(href)
                if not profile_url or profile_url in seen:
                    continue
                seen.add(profile_url)

                # Name — the first meaningful text inside the link or nearby span
                name_el = (
                    card.query_selector('span[aria-hidden="true"]') or
                    card.query_selector('.entity-result__title-text') or
                    link_el
                )
                full_name = _clean(name_el.inner_text()) if name_el else None
                if full_name and _NOISE_RE.search(full_name):
                    full_name = None

                parts = (full_name or '').split(None, 1)
                first_name = parts[0] if parts else None
                last_name = parts[1] if len(parts) > 1 else None

                # Headline / title (primary subtitle)
                subtitle_el = card.query_selector('.entity-result__primary-subtitle')
                headline = _clean(subtitle_el.inner_text()) if subtitle_el else None

                # Location (secondary subtitle)
                loc_el = card.query_selector('.entity-result__secondary-subtitle')
                location = _clean(loc_el.inner_text()) if loc_el else None

                people.append({
                    'linkedin_url': profile_url,
                    'profile_url': profile_url,
                    'first_name': first_name,
                    'last_name': last_name,
                    'title': headline,
                    'location': location,
                    'email': None,
                })
                logger.debug("LinkedIn search found: %s %s — %s", first_name, last_name, headline)

            if len(people) >= limit:
                break

            # Try to click "Next" for more results
            next_btn = self._page.query_selector('button[aria-label="Next"]')
            if not next_btn or not next_btn.is_enabled():
                break
            try:
                next_btn.click()
                self._page.wait_for_timeout(3000)
            except Exception:
                break

        logger.info("LinkedIn search %r — found %d people", keywords, len(people))
        return people

    # ------------------------------------------------------------------ #
    # Profile enrichment                                                   #
    # ------------------------------------------------------------------ #

    def scrape_profile(self, linkedin_url: str) -> Dict[str, Any]:
        """Visit one LinkedIn profile and extract structured data."""
        result: Dict[str, Any] = {
            'first_name': None, 'last_name': None,
            'title': None, 'company': None,
            'email': None, 'about': None,
            'success': False,
        }

        if not self._goto(linkedin_url):
            return result
        if self._is_auth_wall():
            logger.warning("Auth wall visiting profile %s", linkedin_url)
            return result

        # Name
        name_el = (
            self._page.query_selector('h1.text-heading-xlarge') or
            self._page.query_selector('h1[class*="name"]') or
            self._page.query_selector('h1')
        )
        if name_el:
            full_name = _clean(name_el.inner_text())
            if full_name:
                parts = full_name.split(None, 1)
                result['first_name'] = parts[0]
                result['last_name'] = parts[1] if len(parts) > 1 else None

        # Headline / title
        headline_el = (
            self._page.query_selector('div.text-body-medium.break-words') or
            self._page.query_selector('[class*="headline"]')
        )
        if headline_el:
            headline = _clean(headline_el.inner_text())
            if headline and not _NOISE_RE.search(headline):
                result['title'] = headline

        # Current company (first experience item)
        exp_el = (
            self._page.query_selector('section[data-section="experience"] li') or
            self._page.query_selector('section[id*="experience"] li')
        )
        if exp_el:
            co_el = (
                exp_el.query_selector('span.t-14.t-normal') or
                exp_el.query_selector('[class*="company-name"]')
            )
            if co_el:
                result['company'] = _clean(co_el.inner_text())

        # Contact info modal — may expose email
        try:
            contact_btn = (
                self._page.query_selector('a[href*="contact-info"]') or
                self._page.query_selector('a[id*="contact-info"]')
            )
            if contact_btn:
                contact_btn.click()
                self._page.wait_for_timeout(1500)
                email_link = self._page.query_selector('a[href^="mailto:"]')
                if email_link:
                    href = email_link.get_attribute('href') or ''
                    email = href.replace('mailto:', '').strip()
                    if '@' in email:
                        result['email'] = email.lower()
                close_btn = (
                    self._page.query_selector('button[aria-label="Dismiss"]') or
                    self._page.query_selector('button[data-test-modal-close-btn]')
                )
                if close_btn:
                    close_btn.click()
        except Exception as exc:
            logger.debug("Contact info modal error for %s: %s", linkedin_url, exc)

        result['success'] = True
        logger.info(
            "LinkedIn profile scraped %s — name=%s %s title=%s email=%s",
            linkedin_url, result['first_name'], result['last_name'],
            result['title'], result['email'],
        )
        return result


# ------------------------------------------------------------------ #
# Convenience wrappers (used by Celery tasks)                          #
# ------------------------------------------------------------------ #

def scrape_linkedin_profile(
    linkedin_url: str,
    adspower_profile_id: str,
    adspower_api_url: str = 'http://host.docker.internal:50325',
    timeout_ms: int = 20000,
) -> Dict[str, Any]:
    """Single-profile enrichment — opens browser, scrapes, closes."""
    scraper = LinkedInScraper(adspower_profile_id, adspower_api_url, timeout_ms)
    if not scraper.open():
        return {'success': False}
    try:
        return scraper.scrape_profile(linkedin_url)
    finally:
        scraper.close()


def search_and_scrape_linkedin(
    keywords: str,
    adspower_profile_id: str,
    adspower_api_url: str = 'http://host.docker.internal:50325',
    limit: int = 25,
    enrich_profiles: bool = False,
    timeout_ms: int = 20000,
) -> List[Dict[str, Any]]:
    """Search LinkedIn for people, optionally deep-scrape each profile.

    enrich_profiles=False  → fast: returns search card data (name + headline)
    enrich_profiles=True   → slow: visits each profile for email + full data
    """
    scraper = LinkedInScraper(adspower_profile_id, adspower_api_url, timeout_ms)
    if not scraper.open():
        return []
    try:
        people = scraper.search_people(keywords, limit=limit)
        if enrich_profiles:
            for person in people:
                url = person.get('linkedin_url')
                if url:
                    enriched = scraper.scrape_profile(url)
                    if enriched.get('success'):
                        person['first_name'] = enriched.get('first_name') or person.get('first_name')
                        person['last_name'] = enriched.get('last_name') or person.get('last_name')
                        person['title'] = enriched.get('title') or person.get('title')
                        person['email'] = enriched.get('email')
                        person['company'] = enriched.get('company')
                    time.sleep(2)  # polite delay between profile visits
        return people
    finally:
        scraper.close()
