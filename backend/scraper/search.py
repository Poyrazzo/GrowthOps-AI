"""Search-assisted discovery for public person/profile pages.

The direct scraper is still the primary extractor. Search only expands the set
of URLs to crawl when a target site does not link every useful person page.
Default provider is DuckDuckGo HTML because it needs no API key, but public
search pages may challenge automated requests. For production, use serper,
serpapi, or a self-hosted SearxNG instance behind the same interface.
"""
import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from django.conf import settings

logger = logging.getLogger(__name__)

LINKEDIN_PROFILE_RE = re.compile(r'https?://(?:[\w-]+\.)?linkedin\.com/in/[A-Za-z0-9_%\-]+/?', re.I)

SEARCH_TARGET_DOMAINS = (
    'linkedin.com/in',
    'kariyer.net',
    'youthall.com',
    'researchgate.net/profile',
    'academia.edu',
    'orcid.org',
    'edu.tr',
    'edu',
)


def is_linkedin_profile_url(url: str) -> bool:
    return bool(LINKEDIN_PROFILE_RE.search(url or ''))


def _extract_linkedin_url(url: str) -> Optional[str]:
    match = LINKEDIN_PROFILE_RE.search(urllib.parse.unquote(url or ''))
    return match.group(0).rstrip('/') if match else None


def _company_terms(company_name: Optional[str], company_domain: Optional[str]) -> List[str]:
    terms = []
    if company_name:
        terms.append(f'"{company_name}"')
    if company_domain:
        stem = company_domain.split('.', 1)[0].replace('-', ' ')
        if stem and stem.lower() not in (company_name or '').lower():
            terms.append(f'"{stem}"')
    return terms or ['']


def _persona_terms(target_persona: Optional[str]) -> str:
    """Return a short, Serper-safe keyword from the target persona.

    The full persona may be "English Language Teachers, HR Managers, Training Directors"
    which Serper rejects when quoted. We take only the first persona and shorten it.
    """
    if target_persona:
        # Take the first persona before any comma, then max 3 words
        first = target_persona.split(',')[0].strip()
        words = first.split()[:3]
        return ' '.join(words)
    return 'HR manager teacher instructor'


def _clean_result_url(url: str) -> Optional[str]:
    if not url:
        return None
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.endswith('duckduckgo.com') and parsed.path.startswith('/l/'):
        query = urllib.parse.parse_qs(parsed.query)
        url = query.get('uddg', [url])[0]
        parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return None
    if any(url.lower().split('?', 1)[0].endswith(ext) for ext in ('.pdf', '.jpg', '.png', '.gif', '.webp', '.zip')):
        return None
    return url.split('#', 1)[0]


def _result_is_relevant(url: str) -> bool:
    low = (url or '').lower()
    return any(domain in low for domain in SEARCH_TARGET_DOMAINS)


def _duckduckgo_search(query: str, limit: int) -> List[Dict[str, str]]:
    try:
        response = requests.post(
            'https://html.duckduckgo.com/html/',
            data={'q': query},
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; GrowthOpsBot/1.0)',
                'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            },
            timeout=12,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("DuckDuckGo search failed for query=%r: %s", query, exc)
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    page_text = soup.get_text(' ', strip=True).lower()
    if 'please complete the following challenge' in page_text:
        logger.warning("DuckDuckGo challenged search query=%r; configure SEARCH_PROVIDER for reliable discovery.", query)
        return []

    results: List[Dict[str, str]] = []
    for a in soup.select('a.result__a'):
        url = _clean_result_url(a.get('href'))
        if not url:
            continue
        container = a.find_parent(class_='result')
        snippet_el = container.select_one('.result__snippet') if container else None
        results.append({
            'url': url,
            'title': a.get_text(' ', strip=True),
            'snippet': snippet_el.get_text(' ', strip=True) if snippet_el else '',
            'query': query,
        })
        if len(results) >= limit:
            break
    return results


def _serper_search(query: str, limit: int) -> List[Dict[str, str]]:
    api_key = getattr(settings, 'SEARCH_API_KEY', '')
    if not api_key:
        return []
    try:
        response = requests.post(
            'https://google.serper.dev/search',
            headers={'X-API-KEY': api_key, 'Content-Type': 'application/json'},
            json={'q': query, 'num': min(limit, 10)},
            timeout=12,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Serper search failed for query=%r: %s", query, exc)
        return []

    results = []
    for item in response.json().get('organic', [])[:limit]:
        url = _clean_result_url(item.get('link'))
        if not url:
            continue
        results.append({
            'url': url,
            'title': item.get('title') or '',
            'snippet': item.get('snippet') or '',
            'query': query,
        })
    return results


def _serpapi_search(query: str, limit: int) -> List[Dict[str, str]]:
    api_key = getattr(settings, 'SEARCH_API_KEY', '')
    if not api_key:
        return []
    try:
        response = requests.get(
            'https://serpapi.com/search.json',
            params={'engine': 'google', 'q': query, 'api_key': api_key, 'num': limit},
            timeout=12,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("SerpAPI search failed for query=%r: %s", query, exc)
        return []

    results = []
    for item in response.json().get('organic_results', [])[:limit]:
        url = _clean_result_url(item.get('link'))
        if not url:
            continue
        results.append({
            'url': url,
            'title': item.get('title') or '',
            'snippet': item.get('snippet') or '',
            'query': query,
        })
    return results


def _searxng_search(query: str, limit: int) -> List[Dict[str, str]]:
    base_url = getattr(settings, 'SEARCH_BASE_URL', '').rstrip('/')
    if not base_url:
        return []
    try:
        response = requests.get(
            f'{base_url}/search',
            params={'q': query, 'format': 'json', 'language': 'tr-TR'},
            headers={'User-Agent': 'Mozilla/5.0 (compatible; GrowthOpsBot/1.0)'},
            timeout=12,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("SearxNG search failed for query=%r: %s", query, exc)
        return []

    results = []
    for item in response.json().get('results', [])[:limit]:
        url = _clean_result_url(item.get('url'))
        if not url:
            continue
        results.append({
            'url': url,
            'title': item.get('title') or '',
            'snippet': item.get('content') or '',
            'query': query,
        })
    return results


def search_web(query: str, limit: int = 10) -> List[Dict[str, str]]:
    provider = getattr(settings, 'SEARCH_PROVIDER', 'duckduckgo').lower()
    if provider == 'serper':
        return _serper_search(query, limit)
    if provider == 'serpapi':
        return _serpapi_search(query, limit)
    if provider == 'searxng':
        return _searxng_search(query, limit)
    return _duckduckgo_search(query, limit)


def parse_person_from_search_result(result: Dict[str, str]) -> Dict[str, Optional[str]]:
    title = result.get('title') or ''
    primary = re.split(r'\s[-|–]\s', title, maxsplit=1)[0]
    primary = re.sub(r'\s+\|\s+(LinkedIn|Kariyer|Youthall|ResearchGate).*$',
                     '', primary, flags=re.I).strip()
    tokens = [t for t in re.split(r'\s+', primary) if t.replace('.', '').isalpha()]
    first_name = tokens[0].title() if len(tokens) >= 2 else None
    last_name = tokens[-1].title() if len(tokens) >= 2 else None
    return {
        'first_name': first_name,
        'last_name': last_name,
        'title': result.get('snippet') or None,
    }


def build_person_search_queries(
    company_name: Optional[str],
    company_domain: Optional[str],
    target_persona: Optional[str],
) -> List[str]:
    persona = _persona_terms(target_persona)
    queries: List[str] = []
    for company in _company_terms(company_name, company_domain):
        queries.extend([
            f'{company} {persona} linkedin.com/in',
            f'{company} {persona} email iletisim',
            f'{company} kariyer.net',
        ])
    return queries


def discover_person_pages(
    company_name: Optional[str],
    company_domain: Optional[str],
    target_persona: Optional[str],
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Find likely public profile/person pages for a company/persona target."""
    seen = set()
    discovered: List[Dict[str, Any]] = []
    for query in build_person_search_queries(company_name, company_domain, target_persona):
        for result in search_web(query, limit=limit):
            url = result.get('url')
            if not url or url.lower() in seen or not _result_is_relevant(url):
                continue
            seen.add(url.lower())
            linkedin_url = _extract_linkedin_url(url)
            if linkedin_url:
                result['url'] = linkedin_url
            discovered.append(result)
            if len(discovered) >= limit:
                return discovered
    return discovered
