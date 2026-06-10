import pandas as pd
import numpy as np
from typing import List, Dict, Any

# Mailbox prefixes that indicate a generic/role inbox rather than a person (SRS 3.6)
GENERIC_EMAIL_PREFIXES = {
    'info', 'support', 'sales', 'contact', 'hello', 'admin', 'office',
    'mail', 'help', 'team', 'hr', 'jobs', 'careers', 'marketing',
    'press', 'billing', 'noreply', 'no-reply', 'webmaster', 'postmaster'
}

class DataCleaner:
    """
    Pandas-powered utility to normalize, deduplicate, and filter raw scraped leads
    before they are inserted into the database.
    """

    def __init__(self, raw_data_list: List[Dict[str, Any]]):
        # Convert list of dicts to a pandas DataFrame
        self.df = pd.DataFrame(raw_data_list)

        # Ensure standard columns exist even if empty
        expected_columns = ['email', 'linkedin_url', 'first_name', 'last_name', 'url']
        for col in expected_columns:
            if col not in self.df.columns:
                self.df[col] = None

    @staticmethod
    def _clean_str(value, lower: bool = False):
        """Strips a value to a clean string, preserving None (never the strings 'None'/'nan')."""
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        text = str(value).strip()
        if not text or text.lower() in ('none', 'nan'):
            return None
        return text.lower() if lower else text

    def _normalize_text(self):
        """Trims whitespace and converts emails to lowercase. None values stay None."""
        self.df['email'] = self.df['email'].map(lambda v: self._clean_str(v, lower=True))

    def _normalize_urls(self):
        """Ensures URLs have https:// prefix and no trailing slashes. None values stay None."""
        def clean_url(value):
            text = DataCleaner._clean_str(value)
            if text is None:
                return None
            if not text.startswith('http'):
                text = 'https://' + text
            return text.rstrip('/')

        for col in ['url', 'linkedin_url']:
            self.df[col] = self.df[col].map(clean_url)

    def _clean_names(self):
        """Capitalizes First and Last names correctly (Title Case). None values stay None."""
        def clean_name(value):
            text = DataCleaner._clean_str(value)
            return text.title() if text else None

        for col in ['first_name', 'last_name']:
            self.df[col] = self.df[col].map(clean_name)

    def _flag_generic_emails(self):
        """Flags role-based inboxes (info@, support@, ...) so they can be human-reviewed (SRS 3.6)."""
        def is_generic(email):
            if not email or '@' not in email:
                return False
            local_part = email.split('@')[0]
            return local_part in GENERIC_EMAIL_PREFIXES

        self.df['is_generic_email'] = self.df['email'].map(is_generic)

    def _filter_invalid(self):
        """Drops leads that have NEITHER an email NOR a linkedin_url."""
        # We need at least one contact method
        mask = self.df['email'].notna() | self.df['linkedin_url'].notna()
        self.df = self.df[mask]

    def _deduplicate(self):
        """Removes duplicates based on email or linkedin_url.

        Critically, rows whose key is null must NOT be treated as duplicates of each
        other (pandas drop_duplicates considers NaN/None values equal, which used to
        collapse every email-only or linkedin-only batch into a single lead).
        """
        for col in ['email', 'linkedin_url']:
            has_key = self.df[self.df[col].notna()].drop_duplicates(subset=[col], keep='first')
            no_key = self.df[self.df[col].isna()]
            self.df = pd.concat([has_key, no_key])

    def process(self) -> List[Dict[str, Any]]:
        """Orchestrates the cleaning pipeline and returns a list of cleaned dicts."""
        if self.df.empty:
            return []

        self._normalize_text()
        self._normalize_urls()
        self._clean_names()
        self._flag_generic_emails()
        self._filter_invalid()
        self._deduplicate()

        # Convert back to list of dicts, replacing NaN/NaT with None
        self.df = self.df.replace({np.nan: None})
        return self.df.to_dict(orient='records')
