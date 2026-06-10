import pandas as pd
import numpy as np
from typing import List, Dict, Any

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

    def _normalize_text(self):
        """Trims whitespace and converts emails to lowercase."""
        if 'email' in self.df.columns:
            self.df['email'] = self.df['email'].astype(str).str.strip().str.lower()
            # Replace 'nan' string (from pandas casting) back to None
            self.df['email'] = self.df['email'].replace({'nan': None, '': None})

    def _normalize_urls(self):
        """Ensures URLs have https:// prefix and no trailing slashes."""
        for col in ['url', 'linkedin_url']:
            if col in self.df.columns:
                self.df[col] = self.df[col].astype(str).str.strip()
                # Add https:// if missing
                mask = ~self.df[col].str.startswith('http', na=False) & (self.df[col] != 'nan') & (self.df[col] != 'None') & (self.df[col] != '')
                self.df.loc[mask, col] = 'https://' + self.df.loc[mask, col]
                # Remove trailing slashes
                self.df[col] = self.df[col].str.rstrip('/')
                # Clean up nan/None
                self.df[col] = self.df[col].replace({'nan': None, 'None': None, '': None})

    def _clean_names(self):
        """Capitalizes First and Last names correctly (Title Case)."""
        for col in ['first_name', 'last_name']:
            if col in self.df.columns:
                self.df[col] = self.df[col].astype(str).str.strip().str.title()
                self.df[col] = self.df[col].replace({'Nan': None, 'None': None, '': None})

    def _filter_invalid(self):
        """Drops leads that have NEITHER an email NOR a linkedin_url."""
        # We need at least one contact method
        mask = self.df['email'].notna() | self.df['linkedin_url'].notna()
        self.df = self.df[mask]

    def _deduplicate(self):
        """Removes duplicates based on email or linkedin_url."""
        # Sort by email so None values are at the bottom, then drop duplicates
        if 'email' in self.df.columns:
            self.df = self.df.sort_values('email').drop_duplicates(subset=['email'], keep='first')
        if 'linkedin_url' in self.df.columns:
            self.df = self.df.sort_values('linkedin_url').drop_duplicates(subset=['linkedin_url'], keep='first')

    def process(self) -> List[Dict[str, Any]]:
        """Orchestrates the cleaning pipeline and returns a list of cleaned dicts."""
        if self.df.empty:
            return []

        self._normalize_text()
        self._normalize_urls()
        self._clean_names()
        self._filter_invalid()
        self._deduplicate()

        # Convert back to list of dicts, replacing NaN/NaT with None
        self.df = self.df.replace({np.nan: None})
        return self.df.to_dict(orient='records')
