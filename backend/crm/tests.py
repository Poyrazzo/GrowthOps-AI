from bs4 import BeautifulSoup
from django.test import TestCase

from scraper.cleaner import DataCleaner
from scraper.extractor import extract_contacts, guess_name_from_email


class HumanLeadExtractionTests(TestCase):
    def test_branch_inbox_is_not_treated_as_a_person_name(self):
        self.assertEqual(
            guess_name_from_email('hakkarisube@englishtime.com'),
            {'first_name': None, 'last_name': None},
        )

        cleaned = DataCleaner([
            {'email': 'nigde.sube@englishtime.com'},
            {'email': 'hakkarisube@englishtime.com'},
            {'email': 'ayse.yilmaz@example.com'},
        ]).process()

        generic_by_email = {row['email']: row['is_generic_email'] for row in cleaned}
        self.assertTrue(generic_by_email['nigde.sube@englishtime.com'])
        self.assertTrue(generic_by_email['hakkarisube@englishtime.com'])
        self.assertFalse(generic_by_email['ayse.yilmaz@example.com'])

    def test_staff_card_with_linkedin_only_becomes_human_contact(self):
        html = """
        <section class="team-card">
          <h3>Ayse Yilmaz</h3>
          <p class="role">English Teacher</p>
          <a href="https://www.linkedin.com/in/ayse-yilmaz">LinkedIn</a>
        </section>
        """
        soup = BeautifulSoup(html, 'html.parser')

        contacts = extract_contacts(soup, html)

        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0]['linkedin_url'], 'https://www.linkedin.com/in/ayse-yilmaz')
        self.assertEqual(contacts[0]['first_name'], 'Ayse')
        self.assertEqual(contacts[0]['last_name'], 'Yilmaz')
        self.assertEqual(contacts[0]['title'], 'English Teacher')
