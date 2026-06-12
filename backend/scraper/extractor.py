"""Contact-extraction engine shared by the static and dynamic scrapers.

Beyond a naive email regex sweep this engine:
  * reads mailto: links (highest quality — often carries name + title in the anchor)
  * de-obfuscates "name [at] domain [dot] com" / HTML-entity / spaced variants
  * scans raw HTML and visible text with a strict email regex
  * parses schema.org Person / vCard markup for structured name+title+email triples
  * looks for staff/team card patterns (name+title blocks that sit next to an email)
  * filters junk (asset filenames, tracking pixels, placeholder/demo addresses)
  * infers first/last name from mailto anchor text or the email local-part
  * discovers contact/team/about/staff sub-pages to crawl (multilingual incl. Turkish)
"""
import re
import html as html_lib
import urllib.parse
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup, Tag

# ---------------------------------------------------------------------------
# Regexes & constants
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')

_ASSET_SUFFIXES = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg',
                   '.css', '.js', '.ico', '.bmp', '.tiff', '.woff', '.woff2')

_JUNK_LOCALPARTS = {
    'example', 'test', 'youremail', 'your-email', 'email', 'name',
    'username', 'user', 'demo', 'sample', 'firstname', 'lastname', 'someone',
    'you', 'hello', 'hi', 'hey', 'me', 'placeholder',
}

_ROLE_LOCALPART_WORDS = {
    'info', 'contact', 'sales', 'support', 'hello', 'admin', 'office',
    'mail', 'help', 'team', 'hr', 'jobs', 'careers', 'marketing',
    'press', 'billing', 'iletisim', 'bilgi', 'destek', 'kurumsal',
    'ik', 'kayit', 'basvuru', 'musteri', 'merhaba',
    'sube', 'şube', 'branch', 'branches', 'office', 'campus',
    'noreply', 'no-reply', 'webmaster', 'postmaster',
}
_JUNK_DOMAINS = {
    'example.com', 'example.org', 'domain.com', 'yourdomain.com', 'email.com',
    'sentry.io', 'wixpress.com', 'sentry.wixpress.com', 'godaddy.com',
    'schema.org', 'w3.org', 'googleapis.com', 'gstatic.com',
}
_JUNK_SUBSTRINGS = ('@sentry', 'sentry.', '.wixpress', '@2x', '@3x')

# Link text/href fragments that signal a contact/about/team page worth crawling.
_CONTACT_HINTS = (
    'contact', 'contacts', 'iletisim', 'iletişim', 'bize-ulasin', 'bize-ulaşın',
    'reach', 'get-in-touch', 'imprint', 'impressum',
    'about', 'about-us', 'hakkimizda', 'hakkımızda', 'hakkinda', 'hakkında',
    'who-we-are', 'kim-biz', 'kurumsal', 'company',
    'team', 'our-team', 'ekip', 'ekibimiz', 'kadro', 'kadromuz',
    'staff', 'people', 'personel', 'personeller', 'calisan', 'çalışan',
    'faculty', 'academic', 'akademik', 'akademik-kadro', 'akademik-personel',
    'instructor', 'instructors', 'teacher', 'teachers', 'trainer', 'trainers',
    'ogretmen', 'öğretmen', 'ogretmenler', 'öğretmenler',
    'egitmen', 'eğitmen', 'egitmenler', 'eğitmenler',
    'consultant', 'consultants', 'uzman', 'uzmanlar', 'danisman', 'danışman',
    'management', 'yonetim', 'yönetim', 'leadership', 'director',
    'board', 'advisory', 'kurucu', 'kurucular',
    'career', 'careers', 'kariyer', 'insan-kaynaklari', 'insan-kaynakları',
    'hr', 'human-resources', 'talent', 'recruitment',
    'member', 'members', 'uye', 'üye', 'uyeler', 'üyeler',
    'profile', 'profiles', 'profil', 'profiller',
    'hizmet', 'services',
)

# Turkish + English job title keywords used when inferring titles from surrounding text.
_TITLE_KEYWORDS = (
    # Turkish
    'müdür', 'mudur', 'direktör', 'direktor', 'yönetici', 'yonetici',
    'koordinatör', 'koordinator', 'eğitmen', 'egitmen', 'öğretmen', 'ogretmen',
    'uzman', 'danışman', 'danisman', 'kurucu', 'ortak', 'başkan', 'baskan',
    'genel müdür', 'genel mudur', 'okul müdürü', 'okul mudduru',
    'insan kaynakları', 'ik uzmanı',
    # English
    'director', 'manager', 'coordinator', 'trainer', 'teacher', 'instructor',
    'principal', 'head of', 'head teacher', 'ceo', 'coo', 'founder', 'partner',
    'consultant', 'specialist', 'supervisor', 'officer', 'executive',
    'learning', 'development', 'hr ', 'human resources', 'talent',
    'academic', 'dean', 'professor', 'lecturer', 'tutor',
)

# Schema.org type names that represent a person.
_SCHEMA_PERSON_TYPES = {'Person', 'Employee', 'JobPosting'}

# CSS class/id fragments that suggest a staff card container.
_CARD_CLASS_HINTS = (
    'team', 'staff', 'member', 'person', 'ekip', 'kadro', 'trainer',
    'teacher', 'instructor', 'faculty', 'employee', 'card', 'bio',
    'profile', 'people', 'speaker', 'expert', 'uzman',
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _deobfuscate(text: str) -> str:
    if not text:
        return ''
    t = html_lib.unescape(text)
    t = t.replace('&#64;', '@').replace('&#46;', '.')
    t = re.sub(r'\s*[\[\(\{]\s*at\s*[\]\)\}]\s*', '@', t, flags=re.I)
    t = re.sub(r'\s+at\s+', '@', t, flags=re.I)
    t = re.sub(r'\s*[\[\(\{]\s*dot\s*[\]\)\}]\s*', '.', t, flags=re.I)
    t = re.sub(r'\s+dot\s+', '.', t, flags=re.I)
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
    tld = domain.rsplit('.', 1)[-1]
    if not tld.isalpha() or len(tld) < 2:
        return True
    return False


def guess_name_from_email(email: str) -> Dict[str, Optional[str]]:
    """john.doe@x.com -> first='John', last='Doe'. Returns Nones for role/opaque inboxes."""
    local = email.split('@', 1)[0].lower()
    local = re.sub(r'\d+$', '', local)
    parts = re.split(r'[._\-]+', local)
    parts = [p for p in parts if p]
    compact_local = ''.join(parts)
    if (
        not parts
        or any(p in _ROLE_LOCALPART_WORDS for p in parts)
        or compact_local.endswith(('sube', 'şube', 'branch', 'office'))
    ):
        return {'first_name': None, 'last_name': None}
    if len(parts) == 1:
        if len(parts[0]) <= 2:
            return {'first_name': None, 'last_name': None}
        return {'first_name': parts[0].title(), 'last_name': None}
    return {'first_name': parts[0].title(), 'last_name': parts[1].title()}


def _name_from_text(text: str) -> Dict[str, Optional[str]]:
    """Parse 'First Last' anchor text into name parts."""
    if not text:
        return {'first_name': None, 'last_name': None}
    text = text.strip()
    if '@' in text or len(text) > 50:
        return {'first_name': None, 'last_name': None}
    tokens = [t for t in re.split(r'\s+', text) if t.isalpha() and len(t) > 1]
    if len(tokens) == 2:
        return {'first_name': tokens[0].title(), 'last_name': tokens[1].title()}
    if len(tokens) == 3:
        return {'first_name': tokens[0].title(), 'last_name': tokens[2].title()}
    return {'first_name': None, 'last_name': None}


def _extract_title_from_nearby(element: Tag) -> Optional[str]:
    """Scan siblings and parent children near an element for a job title string."""
    candidates = []

    # Check immediate parent and grandparent siblings
    for ancestor in [element.parent, element.parent.parent if element.parent else None]:
        if not ancestor:
            continue
        for sibling in list(ancestor.children):
            if not hasattr(sibling, 'get_text'):
                continue
            text = sibling.get_text(separator=' ', strip=True)
            if 2 < len(text) < 120:
                candidates.append(text)

    for text in candidates:
        low = text.lower()
        if any(kw in low for kw in _TITLE_KEYWORDS):
            # Clean up — drop lines that are just URLs or emails
            if '@' in text or 'http' in text:
                continue
            # Return the first line that looks like a title
            for line in text.splitlines():
                line = line.strip()
                if 2 < len(line) < 80 and any(kw in line.lower() for kw in _TITLE_KEYWORDS):
                    return line
    return None


def _parse_schema_persons(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract structured name+title+email from schema.org Person markup."""
    results = []
    for tag in soup.find_all(attrs={'itemtype': True}):
        itype = tag.get('itemtype', '')
        if not any(pt in itype for pt in _SCHEMA_PERSON_TYPES):
            continue
        name_el = tag.find(attrs={'itemprop': 'name'})
        title_el = tag.find(attrs={'itemprop': re.compile(r'jobTitle|title|position', re.I)})
        email_el = tag.find(attrs={'itemprop': 'email'})
        email = None
        if email_el:
            raw = email_el.get('content') or email_el.get_text()
            matches = EMAIL_RE.findall(raw)
            if matches:
                email = matches[0].lower()
        if not email:
            # Try to find a mailto: anywhere inside the block
            a = tag.find('a', href=re.compile(r'^mailto:', re.I))
            if a:
                email = a['href'][7:].split('?')[0].strip().lower()
        if not email:
            continue
        name_text = name_el.get_text(strip=True) if name_el else ''
        title_text = title_el.get_text(strip=True) if title_el else None
        names = _name_from_text(name_text)
        results.append({
            'email': email,
            'first_name': names['first_name'],
            'last_name': names['last_name'],
            'title': title_text,
        })
    return results


def _parse_staff_cards(soup: BeautifulSoup, source_url: str = '') -> List[Dict[str, Any]]:
    """Find staff/team card containers and extract name+title+email from each.

    Cards with a name+title but no email or LinkedIn are still returned — the
    source_url is stored as profile_url so the lead can be identified and later
    enriched via LinkedIn search or AdsPower.
    """
    results = []

    def _looks_like_card(tag: Tag) -> bool:
        classes = ' '.join(tag.get('class', [])).lower()
        id_ = (tag.get('id') or '').lower()
        return any(h in classes or h in id_ for h in _CARD_CLASS_HINTS)

    cards = [t for t in soup.find_all(True) if _looks_like_card(t)]
    # De-duplicate: skip cards that are children of another card already collected
    filtered = []
    for card in cards:
        if not any(card in c.descendants for c in filtered):
            filtered.append(card)

    for card in filtered:
        email = None
        a_mail = card.find('a', href=re.compile(r'^mailto:', re.I))
        if a_mail:
            email = a_mail['href'][7:].split('?')[0].strip().lower()
        if not email:
            text = card.get_text(' ')
            matches = EMAIL_RE.findall(_deobfuscate(text))
            if matches:
                email = matches[0].lower()
        if email and _is_junk_email(email):
            email = None

        linkedin_url = None
        a_linkedin = card.find('a', href=re.compile(r'linkedin\.com/in/', re.I))
        if a_linkedin:
            linkedin_url = a_linkedin['href'].strip()

        # Name: prefer heading tags inside the card
        name_text = ''
        for h_tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'b']:
            h = card.find(h_tag)
            if h:
                name_text = h.get_text(strip=True)
                break

        names = _name_from_text(name_text)
        has_name = bool(names['first_name'] or names['last_name'])

        # Skip cards with no contact method AND no extractable name — nothing to save
        if not email and not linkedin_url and not has_name:
            continue

        # Title: look for a <p>, <span>, or <div> after the name heading that
        # contains a title keyword, or has a role-suggesting class
        title_text = None
        for el in card.find_all(['p', 'span', 'div', 'small']):
            cl = ' '.join(el.get('class', [])).lower()
            text = el.get_text(strip=True)
            if not text or len(text) > 120:
                continue
            if any(h in cl for h in ('title', 'role', 'position', 'job', 'unvan')):
                title_text = text
                break
            if any(kw in text.lower() for kw in _TITLE_KEYWORDS):
                title_text = text
                break

        # For name+title-only cards (no email, no LinkedIn), set profile_url to
        # the source page so the lead has at least one contact anchor.
        profile_url = None
        if not email and not linkedin_url:
            profile_url = source_url or None

        results.append({
            'email': email,
            'linkedin_url': linkedin_url,
            'profile_url': profile_url,
            'first_name': names['first_name'],
            'last_name': names['last_name'],
            'title': title_text,
        })

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_contacts(soup: BeautifulSoup, raw_html: str, source_url: str = '') -> List[Dict[str, Any]]:
    """Return a deduped list of contact dicts.

    source_url — the URL being scraped; used as profile_url fallback for staff
    cards that have a name+title but no email or LinkedIn link.

    Priority (highest → lowest):
      1. schema.org Person blocks
      2. Staff/team card heuristic
      3. mailto: links (anchor text carries name)
      4. Regex over de-obfuscated HTML / visible text
    """
    by_key: Dict[str, Dict[str, Any]] = {}

    def _add(email=None, first=None, last=None, title=None,
             linkedin_url=None, profile_url=None):
        email = email.strip().strip('.').lower() if email else None
        linkedin_url = linkedin_url.strip() if linkedin_url else None
        if email and _is_junk_email(email):
            return

        # Determine dedup key
        if email:
            key = f"email:{email}"
        elif linkedin_url:
            key = f"linkedin:{linkedin_url.lower().rstrip('/')}"
        elif profile_url and (first or last):
            # Name-only lead anchored by source page — key by name to keep individuals separate
            key = f"name:{(first or '')}_{(last or '')}@{profile_url.rstrip('/')}"
        else:
            return  # no contact method at all — skip

        existing = by_key.get(key)
        if existing is None:
            guess = guess_name_from_email(email) if email else {'first_name': None, 'last_name': None}
            by_key[key] = {
                'email': email,
                'linkedin_url': linkedin_url,
                'profile_url': profile_url,
                'first_name': first or guess['first_name'],
                'last_name': last or guess['last_name'],
                'title': title,
            }
        else:
            if linkedin_url and not existing.get('linkedin_url'):
                existing['linkedin_url'] = linkedin_url
            if profile_url and not existing.get('profile_url'):
                existing['profile_url'] = profile_url
            if first and not existing.get('first_name'):
                existing['first_name'] = first
            if last and not existing.get('last_name'):
                existing['last_name'] = last
            if title and not existing.get('title'):
                existing['title'] = title

    # 1) schema.org structured data — most reliable
    for p in _parse_schema_persons(soup):
        _add(p.get('email'), p.get('first_name'), p.get('last_name'),
             p.get('title'), p.get('linkedin_url'))

    # 2) Staff/team card heuristic — now returns name-only cards with profile_url set
    for p in _parse_staff_cards(soup, source_url=source_url):
        _add(p.get('email'), p.get('first_name'), p.get('last_name'),
             p.get('title'), p.get('linkedin_url'), p.get('profile_url'))

    # 3) mailto: links — good quality, often carry name
    for a in soup.find_all('a', href=True):
        href = a['href']
        if not href.lower().startswith('mailto:'):
            continue
        addr = href[7:].split('?', 1)[0].strip()
        addr = urllib.parse.unquote(addr)
        for piece in re.split(r'[;,]', addr):
            piece = piece.strip()
            if not piece:
                continue
            anchor = _name_from_text(a.get_text())
            title = _extract_title_from_nearby(a)
            _add(piece, anchor['first_name'], anchor['last_name'], title)

    # 4) Regex sweep over de-obfuscated HTML and visible text
    for source_text in (_deobfuscate(raw_html), _deobfuscate(soup.get_text(' '))):
        for match in EMAIL_RE.findall(source_text):
            _add(match)

    return list(by_key.values())


def common_person_page_links(base_url: str, limit: int = 8) -> List[str]:
    """Generate likely staff/person pages even when the site does not link them.

    Many Turkish education sites expose human pages at predictable paths but
    omit them from the public nav, especially on branch/contact pages.
    """
    paths = (
        '/ekibimiz', '/ekip', '/kadromuz', '/egitmenlerimiz',
        '/eğitmenlerimiz', '/ogretmenlerimiz', '/öğretmenlerimiz',
        '/akademik-kadro', '/akademik-personel', '/akademik-kadromuz',
        '/akademik-staff', '/akademik', '/faculty', '/faculty-members',
        '/ogretim-elemanlari', '/öğretim-elemanları', '/ogretim-uyeleri',
        '/öğretim-üyeleri', '/akademisyenler', '/hocalarimiz',
        '/hocalarımız', '/personel', '/calisanlar', '/çalışanlar',
        '/yonetim', '/yönetim', '/yonetim-kurulu', '/yönetim-kurulu',
        '/liderlik', '/kurucular', '/danismanlar', '/danışmanlar',
        '/uzmanlar', '/insan-kaynaklari', '/insan-kaynakları',
        '/kariyer', '/uyeler', '/üyeler', '/uye-listesi', '/üye-listesi',
        '/profiller', '/profil', '/hakkimizda', '/hakkımızda',
        '/hakkinda', '/hakkında', '/kurumsal',
        '/team', '/our-team', '/staff', '/our-staff', '/teachers',
        '/trainers', '/instructors', '/people', '/profiles', '/members',
        '/leadership', '/management', '/board', '/advisors',
        '/consultants', '/experts', '/about', '/about-us', '/who-we-are',
        '/human-resources', '/careers', '/talent',
    )
    parsed = urllib.parse.urlparse(base_url if base_url.startswith('http') else f'https://{base_url}')
    root = f"{parsed.scheme}://{parsed.netloc}"
    return [urllib.parse.urljoin(root, path) for path in paths[:limit]]


def find_contact_links(soup: BeautifulSoup, base_url: str, limit: int = 6) -> List[str]:
    """Find same-domain contact/about/team/staff sub-pages worth crawling."""
    base = urllib.parse.urlparse(base_url)
    base_host = base.netloc.lower()
    found: List[str] = []
    seen = {base_url.rstrip('/')}

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
            continue
        clean = absolute.split('#', 1)[0].rstrip('/')
        if clean in seen:
            continue
        seen.add(clean)
        found.append(clean)
        if len(found) >= limit:
            break
    return found


def find_listing_links(soup: BeautifulSoup, base_url: str, limit: int = 30) -> List[str]:
    """For directory/listing pages: find links to individual profile or school pages.

    Heuristic: links that contain path segments typical of individual listings
    (/profil/, /ilan/, /hoca/, /kurs/, /okul/, /school/, /trainer/, /teacher/)
    and are on the same host.
    """
    _LISTING_HINTS = (
        '/profil', '/profile', '/profiller', '/profiles',
        '/ilan', '/job', '/jobs', '/is-ilani', '/iş-ilanı',
        '/listing', '/listings', '/detail', '/details', '/view',
        '/member', '/members', '/uye', '/üye', '/uyeler', '/üyeler',
        '/person', '/people', '/staff', '/faculty', '/academic',
        '/hoca', '/ogretmen', '/öğretmen', '/egitmen', '/eğitmen',
        '/akademisyen', '/danisman', '/danışman', '/uzman',
        '/kurs', '/okul', '/egitim', '/eğitim',
        '/school', '/trainer', '/teacher', '/tutor', '/instructor',
        '/mentor', '/coach', '/consultant', '/expert',
        '/firma', '/company', '/provider', '/kurum', '/universite', '/üniversite',
    )

    base = urllib.parse.urlparse(base_url)
    base_host = base.netloc.lower()
    found: List[str] = []
    seen: set = set()

    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if not href or href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
            continue
        hint = href.lower()
        if not any(h in hint for h in _LISTING_HINTS):
            continue
        absolute = urllib.parse.urljoin(base_url, href)
        parsed = urllib.parse.urlparse(absolute)
        if parsed.netloc.lower() != base_host:
            continue
        clean = absolute.split('#', 1)[0].rstrip('/')
        if clean in seen or clean == base_url.rstrip('/'):
            continue
        seen.add(clean)
        found.append(clean)
        if len(found) >= limit:
            break
    return found


def extract_social_links(soup: BeautifulSoup) -> Dict[str, Any]:
    """Company LinkedIn page vs individual profiles, plus twitter/X."""
    socials: Dict[str, Any] = {'linkedin_profiles': []}
    seen: set = set()
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
