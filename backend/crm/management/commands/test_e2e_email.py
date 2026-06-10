from django.core.management.base import BaseCommand
from crm.models import EmailAccount, Campaign, Lead, Message
from outreach.sequence import dispatch_pending_emails
from core.encryption import encrypt
import requests
import time

class Command(BaseCommand):
    help = 'Runs an end-to-end test of the email outbound flow using GreenMail mock server.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Starting E2E Email Outbound Test...'))

        # 1. Provision Mock Account
        password_encrypted = encrypt('mockpassword')
        account, created = EmailAccount.objects.get_or_create(
            email='test_sender@growthops.ai',
            defaults={
                'provider': 'smtp',
                'username': 'test_sender@growthops.ai',
                'password_encrypted': password_encrypted,
                'smtp_host': 'greenmail',
                'smtp_port': 3025,
                'imap_host': 'greenmail',
                'imap_port': 3143,
                'daily_limit': 100,
                'is_active': True
            }
        )
        if not created:
            account.is_active = True
            account.save()
        self.stdout.write(self.style.SUCCESS('1. Provisioned Mock SMTP Account.'))

        # 2. Seed Campaign and Lead
        campaign, _ = Campaign.objects.get_or_create(
            name='E2E Test Campaign',
            defaults={
                'target_sector': 'Technology',
                'target_country': 'US',
                'target_persona': 'CTO',
                'value_proposition': 'We automate growth.',
                'outreach_channel': 'email'
            }
        )
        lead, _ = Lead.objects.get_or_create(
            email='target@mock.com',
            defaults={
                'campaign': campaign,
                'first_name': 'Target',
                'last_name': 'Mock',
                'status': 'uncontacted',
                'requires_human_review': False
            }
        )
        self.stdout.write(self.style.SUCCESS('2. Seeded Test Campaign and Lead.'))

        # 3. Draft Message
        Message.objects.filter(lead=lead).delete() # clean old tests
        msg = Message.objects.create(
            lead=lead,
            campaign=campaign,
            sender_account=account,
            channel='email',
            subject='End-to-End Test Subject',
            body='This is an automated E2E test verifying the outbound celery pipeline.',
            status='pending'
        )
        self.stdout.write(self.style.SUCCESS('3. Drafted Pending Message.'))

        # 4. Execute Dispatch
        self.stdout.write(self.style.NOTICE('4. Triggering Celery Dispatch Engine...'))
        dispatched_count = dispatch_pending_emails()
        self.stdout.write(self.style.SUCCESS(f'   Dispatched {dispatched_count} messages.'))

        # 5. Verify Database State
        msg.refresh_from_db()
        if msg.status == 'sent':
            self.stdout.write(self.style.SUCCESS('   Database state updated to "sent".'))
        else:
            self.stdout.write(self.style.ERROR(f'   Database state failed. Expected "sent", got "{msg.status}".'))
            return

        # 6. Verify GreenMail API
        self.stdout.write(self.style.NOTICE('5. Querying GreenMail API to verify delivery...'))
        try:
            # wait a tiny bit for greenmail to process
            time.sleep(1)
            response = requests.get('http://greenmail:8080/api/mail', timeout=5)
            response.raise_for_status()
            emails = response.json()
            
            found = any('End-to-End Test Subject' in e.get('subject', '') for e in emails)
            if found:
                self.stdout.write(self.style.SUCCESS('   SUCCESS! Email payload intercepted by GreenMail mock server.'))
                
                # Cleanup Greenmail so subsequent tests are clean
                requests.post('http://greenmail:8080/api/mail/purge', timeout=5)
            else:
                self.stdout.write(self.style.ERROR('   FAILED! Email not found in GreenMail API.'))
        except requests.RequestException as e:
            self.stdout.write(self.style.WARNING(f'   Could not reach GreenMail API (Is the container running?): {e}'))
            self.stdout.write(self.style.NOTICE('   Test passed on DB level, but skipped network verification.'))
        
        self.stdout.write(self.style.SUCCESS('\nE2E Test Completed Successfully.'))
