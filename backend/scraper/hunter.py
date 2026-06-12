"""Hunter.io email enrichment + company-domain email pattern inference.

Hunter.io is a professional email-finding service that has indexed billions of
business email addresses.  Free tier: 25 email-finder lookups / month; paid
plans scale to production volumes.

Set  HUNTER_API_KEY=<your-key>  in .env to enable.  Without it the module
falls back to deterministic email-pattern inference only (no HTTP calls).

Lookup priority inside  infer_email():
  1. Hunter.io email-finder  (direct first_name + last_name + domain lookup)
  2. Pattern detection  via Hunter.io domain-search  (learns the domain format)
  3. Fallback  firstname.lastname@domain  (most common corporate pattern)
"""
import re
import logging
import requests
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

HUNTER_BASE = "https://api.hunter.io/v2"
_TIMEOUT = 10

_PATTERN_FORMATS: Dict[str, str] = {
    'first.last':  '{fn}.{ln}@{domain}',
    'first_last':  '{fn}_{ln}@{domain}',
    'flast':       '{fi}{ln}@{domain}',
    'firstl':      '{fn}{li}@{domain}',
    'first':       '{fn}@{domain}',
    'last':        '{ln}@{domain}',
}


# ---------------------------------------------------------------------------
# Hunter.io API helpers
# ---------------------------------------------------------------------------

def find_email(first_name: str, last_name: str, domain: str,
               api_key: str) -> Optional[Dict[str, Any]]:
    """Direct Hunter.io email-finder for one person at a company domain.

    Returns {'email': str, 'score': int} on success, None on failure.
    score is Hunter.io's 0-100 deliverability confidence.
    """
    try:
        r = requests.get(
            f"{HUNTER_BASE}/email-finder",
            params={
                'domain': domain,
                'first_name': first_name,
                'last_name': last_name,
                'api_key': api_key,
            },
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json().get('data', {})
            email = data.get('email')
            if email:
                logger.info("Hunter.io found %s (score=%s)", email, data.get('score'))
                return {'email': email, 'score': data.get('score', 0)}
        elif r.status_code == 429:
            logger.warning("Hunter.io rate limit reached — monthly quota exhausted")
        elif r.status_code == 401:
            logger.warning("Hunter.io 401 — check HUNTER_API_KEY")
        else:
            logger.debug("Hunter.io email-finder %d: %s", r.status_code, r.text[:200])
    except Exception as e:
        logger.warning("Hunter.io find_email error: %s", e)
    return None


def domain_search(domain: str, api_key: str) -> List[Dict[str, Any]]:
    """Retrieve all emails Hunter.io has indexed for a company domain.

    Each item contains 'value' (email address), 'first_name', 'last_name',
    'position'.  Used by  detect_email_pattern()  to learn the naming
    convention without spending an email-finder lookup.
    """
    try:
        r = requests.get(
            f"{HUNTER_BASE}/domain-search",
            params={'domain': domain, 'api_key': api_key, 'limit': 100},
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            return r.json().get('data', {}).get('emails', [])
    except Exception as e:
        logger.warning("Hunter.io domain_search error: %s", e)
    return []


# ---------------------------------------------------------------------------
# Pattern detection & inference
# ---------------------------------------------------------------------------

def detect_email_pattern(emails: List[Dict[str, Any]]) -> Optional[str]:
    """Infer a domain's email naming convention from known email+name pairs.

    Returns a key from _PATTERN_FORMATS (e.g. 'first.last') or None if the
    sample is too small to detect a dominant pattern.
    """
    counts: Dict[str, int] = {k: 0 for k in _PATTERN_FORMATS}

    for item in emails:
        addr = (item.get('value') or '').lower()
        fn = re.sub(r'[^a-z]', '', (item.get('first_name') or '').lower())
        ln = re.sub(r'[^a-z]', '', (item.get('last_name') or '').lower())
        if not addr or '@' not in addr or not fn or not ln:
            continue
        local = addr.split('@')[0]
        if local == f'{fn}.{ln}':
            counts['first.last'] += 1
        elif local == f'{fn}_{ln}':
            counts['first_last'] += 1
        elif local == f'{fn[0]}{ln}':
            counts['flast'] += 1
        elif local == f'{fn}{ln[0]}':
            counts['firstl'] += 1
        elif local == fn:
            counts['first'] += 1
        elif local == ln:
            counts['last'] += 1

    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else None


def infer_email(first_name: str, last_name: str, domain: str,
                api_key: Optional[str] = None) -> Optional[str]:
    """Generate the most likely email address for a named person at a domain.

    Lookup order:
      1. Hunter.io email-finder  — verified, scored lookup  (requires api_key)
      2. Hunter.io domain-search — detect the domain's pattern, apply it
      3. Fallback  firstname.lastname@domain  (most common corporate default)

    Always returns a string (never raises).  The caller is responsible for
    deciding whether to treat the result as verified or speculative.
    """
    if not first_name or not last_name:
        return None

    fn = re.sub(r'[^a-z]', '', first_name.lower())
    ln = re.sub(r'[^a-z]', '', last_name.lower())
    if not fn or not ln:
        return None

    # Step 1 — direct Hunter.io lookup (most accurate)
    if api_key:
        result = find_email(first_name, last_name, domain, api_key)
        if result and result.get('email'):
            return result['email']

    # Step 2 — domain-pattern detection
    pattern = None
    if api_key:
        known = domain_search(domain, api_key)
        if known:
            pattern = detect_email_pattern(known)

    # Step 3 — apply detected pattern or default to first.last
    fmt = _PATTERN_FORMATS.get(pattern or 'first.last')
    return fmt.format(fn=fn, ln=ln, fi=fn[0], li=ln[0], domain=domain)
