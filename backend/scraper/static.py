import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional

class StaticScraper:
    """
    Utility class for fetching and parsing static HTML content from websites.
    """
    
    # Generic User-Agent to avoid basic bot blocking
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def fetch_html(self, url: str) -> Optional[str]:
        """Fetches raw HTML from the given URL."""
        if not url.startswith('http'):
            url = 'https://' + url

        try:
            response = requests.get(url, headers=self.HEADERS, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def extract_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extracts title and meta description from BeautifulSoup object."""
        metadata = {
            'title': '',
            'description': ''
        }

        # Title
        if soup.title and soup.title.string:
            metadata['title'] = soup.title.string.strip()

        # Meta Description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc:
            meta_desc = soup.find('meta', attrs={'property': 'og:description'})
            
        if meta_desc and meta_desc.get('content'):
            metadata['description'] = meta_desc['content'].strip()

        return metadata

    def extract_visible_text(self, soup: BeautifulSoup) -> str:
        """Strips scripts and styles to return clean text for AI ingestion."""
        # Remove script, style, header, footer, nav tags which add noise
        for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            element.decompose()

        text = soup.get_text(separator=' ', strip=True)
        # Condense multiple spaces/newlines
        clean_text = re.sub(r'\s+', ' ', text)
        return clean_text

    def extract_emails(self, html: str) -> list[str]:
        """Uses regex to find potential emails in raw HTML."""
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, html)
        
        # Deduplicate and filter out common false positives (like .png or sentry traces)
        clean_emails = set()
        for email in emails:
            if not email.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.css', '.js')):
                clean_emails.add(email.lower())
                
        return list(clean_emails)

    def extract_social_links(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extracts common social media profiles."""
        socials = {}
        for a in soup.find_all('a', href=True):
            href = a['href'].lower()
            if 'linkedin.com/company/' in href:
                socials['linkedin'] = a['href']
            elif 'twitter.com/' in href or 'x.com/' in href:
                socials['twitter'] = a['href']
        return socials

    def scrape_website(self, url: str) -> Dict[str, Any]:
        """Orchestrates the entire scraping process and returns structured data."""
        result = {
            'url': url,
            'success': False,
            'metadata': {},
            'body_text': '',
            'emails': [],
            'social_links': {}
        }

        html = self.fetch_html(url)
        if not html:
            return result

        soup = BeautifulSoup(html, 'html.parser')
        
        result['metadata'] = self.extract_metadata(soup)
        result['body_text'] = self.extract_visible_text(soup)
        result['emails'] = self.extract_emails(html)
        result['social_links'] = self.extract_social_links(soup)
        result['success'] = True

        return result
