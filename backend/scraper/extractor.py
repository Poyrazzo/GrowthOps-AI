"""Professional contact-extraction engine shared by the static and dynamic scrapers.

Goes well beyond a naive regex sweep:
  * reads mailto: links (highest-quality source, often carries the person's name)
  * de-obfuscates "name [at] domain [dot] com" / HTML-entity / spaced variants
  * regex-scans both raw HTML and visible text
  * filters junk (image filenames, tracking inboxes, placeholder/demo addresses)
  * infers first/last name from mailto anchor text or the email local-part
  * discovers contact/about/team sub-pages to crawl (multilingual incl. Turkish)
"""
import re
import html as html_lib
import urllib.parse
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup

# A pragmatic, reasonably strict email pattern.
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')

# File extensions that masquerade as emails inside asset names (e.g. logo@2x.png).
_ASSET_SUFFIXES = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.css', '.js', '.ico', '.bmp', '.tiff')

# Local-parts / domains that are never real prospects.
_JUNK_LOCALPARTS = {'example', 'test', 'youremail', 'your-email', 'email', 'name', 'username',
                    'user', 'demo', 'sample', 'firstname', 'lastname', 'someone'}
_JUNK_DOMAINS = {'example.com', 'example.org', 'domain.com', 'yourdomain.com', 'email.com',
                 'sentry.io', 'wixpress.com', 'sentry.wixpress.com', 'godaddy.com',
                 'schema.org', 'w3.org', 'googleapis.com', 'gstatic.com'}
_JUNK_SUBSTRINGS = ('@sentry', 'sentry.', '.wixpress', '@2x', '@3x')

# Link text/href fragments that indicate a contact/about/team page worth crawling.
_CONTACT_HINTS = (
    'contact', 'iletisim', 'about', 'hakkimizda', 'hakkinda', 'team', 'ekip', 'ekibimiz',
    'kadro', 'kadromuz', 'staff', 'people', 'reach', 'get-in-touch', 'bize-ulasin',
    'kurumsal', 'company', 'imprint', 'impressum',
)


def _deobfuscate(text: str) -> str:
    """Turn human/anti-bot obfuscations back into parseable emails."""
    if not text:
        return ''
    t = html_lib.unescape(text)
    # HTML-entity '@' / '.' that survive unescape in odd encodings
    t = t.replace('&#64;', '@').replace('&#46;', '.')
    # " [at] ", "(at)", " at " (word-boundaried), with spaces around
    t = re.sub(r'\s*[\[\(\{]\s*at\s*[\]\)\}]\s*', '@', t, flags=re.I)
    t = re.sub(r'\s+at\s+', '@', t, flags=re.I)
    # " [dot] ", "(dot)", " dot "
    t = re.sub(r'\s*[\[\(\{]\s*dot\s*[\]\)\}]\s*', '.', t, flags=re.I)
    t = re.sub(r'\s+dot\s+', '.', t, flags=re.I)
    # Collapse spaces left around @ and .
    t = re.sub(r'\s*@\s*', '@', t)
    t = re.sub(r'\s*\.\s*', '.', t)
    return t


def _is_junk_email(email: str) -> bool:
    e = email.lower()
    if e.endswith(_ASSET_SUFFIXES):
        return True
    if any(s in e for s in _JUNK_SUBSTRINGS):
        return True
    if '@' not in e:
        return True
    local, _, domain = e.partition('@')
    if local in _JUNK_LOCALPARTS:
        return True
    if domain in _JUNK_DOMAINS:
        return True
    # A domain with a numeric-only or 1-char TLD is junk
    tld = domain.rsplit('.', 1)[-1]
    if not tld.isalpha() or len(tld) < 2:
        return True
    return False


def guess_name_from_email(email: str) -> Dict[str, Optional[str]]:
    """john.doe@x.com -> first 'John', last 'Doe'. Returns Nones for role/opaque inboxes."""
    local = email.split('@', 1)[0].lower()
    # Strip trailing digits (john.doe2 -> john.doe)
    local = re.sub(r'\d+$', '', local)
    parts = re.split(r'[._\-]+', local)
    parts = [p for p in parts if p]
    role_words = {'info', 'contact', 'sales', 'support', 'hello', 'admin', 'office', 'mail',
                  'help', 'team', 'hr', 'jobs', 'careers', 'marketing', 'press', 'billing',
                  'iletisim', 'bilgi', 'destek', 'kurumsal'}
    if not parts or any(p in role_words for p in parts):
        return {'first_name': None, 'last_name': None}
    if len(parts) == 1:
        # Single token like "johnsmith" is too ambiguous to split safely
        if len(parts[0]) <= 2:
            return {'first_name': None, 'last_name': None}
        return {'first_name': parts[0].title(), 'last_name': None}
    return {'first_name': parts[0].title(), 'last_name': parts[1].title()}


def _name_from_text(text: str) -> Dict[str, Optional[str]]:
    """Parse a 'First Last' style anchor text into name parts, if it looks like a name."""
    if not text:
        return {'first_name': None, 'last_name': None}
    text = text.strip()
    if '@' in text or len(text) > 40:
        return {'first_name': None, 'last_name': None}
    tokens = [t for t in re.split(r'\s+', text) if t.isalpha() and len(t) > 1]
    if len(tokens) == 2:
        return {'first_name': tokens[0].title(), 'last_name': tokens[1].title()}
    return {'first_name': None, 'last_name': None}


def extract_contacts(soup: BeautifulSoup, raw_html: str) -> List[Dict[str, Any]]:
    """Return a deduped list of {email, first_name, last_name} from a page.

    mailto: links win (they often carry a human name in the anchor); regex/de-obfuscated
    matches fill in the rest. Names from mailto anchor text override local-part guesses.
    """
    by_email: Dict[str, Dict[str, Any]] = {}

    def _add(email: str, first=None, last=None):
        email = email.strip().strip('.').lower()
        if not email or _is_junk_email(email):
            return
        existing = by_email.get(email)
        if existing is None:
            guess = guess_name_from_email(email)
            by_email[email] = {
                'email': email,
                'first_name': first or guess['first_name'],
                'last_name': last or guess['last_name'],
            }
        else:
            # Upgrade with a better (anchor-text) name if we now have one
            if first and not existing['first_name']:
                existing['first_name'] = first
            if last and not existing['last_name']:
                existing['last_name'] = last

    # 1) mailto: links — highest quality
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.lower().startswith('mailto:'):
            addr = href[7:].split('?', 1)[0].strip()
            addr = urllib.parse.unquote(addr)
            for piece in re.split(r'[;,]', addr):
                piece = piece.strip()
                if not piece:
                    continue
                anchor = _name_from_text(a.get_text())
                _add(piece, anchor['first_name'], anchor['last_name'])

    # 2) regex over de-obfuscated raw HTML and visible text
    for source_text in (_deobfuscate(raw_html), _deobfuscate(soup.get_text(' '))):
        for match in EMAIL_RE.findall(source_text):
            _add(match)

    return list(by_email.values())


def find_contact_links(soup: BeautifulSoup, base_url: str, limit: int = 4) -> List[str]:
    """Find same-domain contact/about/team page URLs worth crawling for more emails."""
    base = urllib.parse.urlparse(base_url)
    base_host = base.netloc.lower()
    found: List[str] = []
    seen = set()

    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if not href or href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
            continue
        text = (a.get_text() or '').lower()
        hint = href.lower()
        if not any(h in hint or h in text for h in _CONTACT_HINTS):
            continue

        absolute = urllib.parse.urljoin(base_url, href)
        parsed = urllib.parse.urlparse(absolute)
        if parsed.netloc.lower() != base_host:
            continue  # stay on-site
        clean = absolute.split('#', 1)[0].rstrip('/')
        if clean in seen or clean.rstrip('/') == base_url.rstrip('/'):
            continue
        seen.add(clean)
        found.append(clean)
        if len(found) >= limit:
            break
    return found


def extract_social_links(soup: BeautifulSoup) -> Dict[str, Any]:
    """Company LinkedIn page vs individual profiles, plus twitter."""
    socials: Dict[str, Any] = {'linkedin_profiles': []}
    seen = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        low = href.lower()
        if 'linkedin.com/company/' in low:
            socials.setdefault('linkedin_company', href)
        elif 'linkedin.com/in/' in low:
            if low not in seen:
                seen.add(low)
                socials['linkedin_profiles'].append(href)
        elif 'twitter.com/' in low or 'x.com/' in low:
            socials.setdefault('twitter', href)
    return socials
