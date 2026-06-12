from unittest.mock import patch

from bs4 import BeautifulSoup
from django.test import TestCase

from ai_engine.lead_profiler import looks_like_clear_non_person_name
from crm.models import ApprovalQueue, Campaign, Lead, LeadSource, Message
from crm.tasks import _normalize_lead_score, _process_and_save_scrape_result
from scraper.cleaner import DataCleaner
from scraper.extractor import extract_contacts, guess_name_from_email


class HumanLeadExtractionTests(TestCase):
    def test_branch_inbox_is_not_treated_as_a_person_name(self):
        self.assertEqual(
            guess_name_from_email('hakkarisube@englishtime.com'),
            {'first_name': None, 'last_name': None},
        )
        self.assertEqual(
            guess_name_from_email('toefl.ibt@sistemdil.com'),
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

    def test_obvious_page_labels_are_removed_before_saving_as_leads(self):
        cleaned = DataCleaner([
            {
                'email': 'toefl.ibt@sistemdil.com',
                'first_name': 'Toefl',
                'last_name': 'Ibt',
                'profile_url': 'https://www.sistemdil.com/kurslar/toefl',
            },
            {
                'first_name': 'Arkadaşınızın',
                'last_name': 'Adresi',
                'profile_url': 'https://www.yenibiris.com/is-ilanlari/ogretmen',
            },
            {
                'email': 'ayse.yilmaz@example.com',
                'first_name': 'Ayse',
                'last_name': 'Yilmaz',
                'title': 'English Teacher',
            },
        ]).process()

        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0]['email'], 'ayse.yilmaz@example.com')

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

    def test_scoring_guard_keeps_uncertain_contactable_leads_out_of_zero_bucket(self):
        lead = Lead(email='teacher@example.com', title='English Teacher')

        score, reason = _normalize_lead_score(lead, {
            'score': 0,
            'reasoning': 'The name is missing, so fit is uncertain.',
            'persona': 'Teacher',
        })

        self.assertEqual(score, 35)
        self.assertIn('manual review', reason)

    def test_scoring_guard_preserves_true_bad_data_zeroes(self):
        lead = Lead(first_name='Contact', last_name='Us', profile_url='https://example.com/contact')

        score, reason = _normalize_lead_score(lead, {
            'score': 0,
            'reasoning': 'This is not a person.',
            'persona': 'Non-Person / Bad Data',
        })

        self.assertEqual(score, 0)
        self.assertEqual(reason, 'This is not a person.')
        self.assertTrue(looks_like_clear_non_person_name('Contact Us'))
        self.assertFalse(looks_like_clear_non_person_name(None))

    def test_completed_campaign_scrape_result_does_not_save_leads(self):
        campaign = Campaign.objects.create(
            name='Stopped Campaign',
            target_sector='Education',
            target_country='TR',
            target_persona='English Teacher',
            value_proposition='Speaking practice',
            outreach_channel='email',
            status='completed',
        )
        source = LeadSource.objects.create(
            url='https://example.com/team',
            source_type='static',
            sector='Education',
            campaign=campaign,
        )

        result = _process_and_save_scrape_result({
            'success': True,
            'url': source.url,
            'contacts': [{
                'email': 'ayse.yilmaz@example.com',
                'first_name': 'Ayse',
                'last_name': 'Yilmaz',
                'title': 'English Teacher',
            }],
            'social_links': {},
            'body_text': 'Our teaching team',
        }, campaign_id=str(campaign.id), source_id=str(source.id))

        self.assertEqual(result['saved'], 0)
        self.assertEqual(Lead.objects.count(), 0)

    def test_active_campaign_scrape_queues_scoring_for_created_lead(self):
        campaign = Campaign.objects.create(
            name='Active Campaign',
            target_sector='Education',
            target_country='TR',
            target_persona='English Teacher',
            value_proposition='Speaking practice',
            outreach_channel='email',
            status='active',
        )
        source = LeadSource.objects.create(
            url='https://example-school.com/team',
            source_type='static',
            sector='Education',
            campaign=campaign,
        )

        with self.settings(CELERY_TASK_ALWAYS_EAGER=False, SEARCH_DISCOVERY_ENABLED=False):
            with patch('crm.tasks.score_lead_task.delay') as score_delay:
                result = _process_and_save_scrape_result({
                    'success': True,
                    'url': source.url,
                    'contacts': [{
                        'email': 'ayse.yilmaz@example-school.com',
                        'first_name': 'Ayse',
                        'last_name': 'Yilmaz',
                        'title': 'English Teacher',
                    }],
                    'social_links': {},
                    'body_text': 'Our teaching team',
                }, campaign_id=str(campaign.id), source_id=str(source.id))

        self.assertEqual(result['saved'], 1)
        self.assertEqual(score_delay.call_count, 1)

    def test_scrape_result_does_not_save_arkadasinizin_adresi(self):
        campaign = Campaign.objects.create(
            name='Active Campaign',
            target_sector='Education',
            target_country='TR',
            target_persona='English Teacher',
            value_proposition='Speaking practice',
            outreach_channel='email',
            status='active',
        )
        source = LeadSource.objects.create(
            url='https://yenibiris.com/is-ilanlari/ogretmen',
            source_type='directory',
            sector='Education',
            campaign=campaign,
        )

        with self.settings(SEARCH_DISCOVERY_ENABLED=False):
            result = _process_and_save_scrape_result({
                'success': True,
                'url': source.url,
                'contacts': [{
                    'first_name': 'Arkadaşınızın',
                    'last_name': 'Adresi',
                    'profile_url': source.url,
                    'title': 'Unknown Title',
                }],
                'social_links': {},
                'body_text': '',
            }, campaign_id=str(campaign.id), source_id=str(source.id))

        self.assertEqual(result['saved'], 0)
        self.assertEqual(Lead.objects.count(), 0)

    def test_approving_message_draft_queues_immediate_dispatch(self):
        campaign = Campaign.objects.create(
            name='Active Campaign',
            target_sector='Education',
            target_country='TR',
            target_persona='English Teacher',
            value_proposition='Speaking practice',
            outreach_channel='email',
            status='active',
        )
        lead = Lead.objects.create(
            email='ayse.yilmaz@example.com',
            first_name='Ayse',
            last_name='Yilmaz',
            campaign=campaign,
            status='uncontacted',
        )
        message = Message.objects.create(
            lead=lead,
            campaign=campaign,
            channel='email',
            subject='Hello',
            body='Body',
            status='needs_review',
        )
        approval = ApprovalQueue.objects.create(
            item_type='message_draft',
            item_id=str(message.id),
            status='pending',
            reason_for_review='Review draft',
        )

        with patch('crm.tasks.dispatch_emails_task.delay') as dispatch_delay:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.patch(
                    f'/api/crm/approvals/{approval.id}/',
                    {'status': 'approved'},
                    content_type='application/json',
                )

        self.assertEqual(response.status_code, 200)
        message.refresh_from_db()
        self.assertEqual(message.status, 'pending')
        self.assertEqual(dispatch_delay.call_count, 1)
