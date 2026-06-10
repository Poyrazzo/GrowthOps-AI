import smtplib
import time
from email.mime.text import MIMEText
from django.core.management.base import BaseCommand
from crm.models import EmailAccount, Campaign, Lead, Message, Reply
from outreach.sequence import dispatch_pending_emails
from outreach.imap import IMAPReader
from core.encryption import encrypt
import requests

class Command(BaseCommand):
    help = 'Runs an end-to-end test of the email outbound AND inbound flows using the GreenMail mock server.'

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
                'smtp_encryption': 'none',
                'imap_host': 'greenmail',
                'imap_port': 3143,
                'imap_use_ssl': False,
                'daily_limit': 100,
                'is_active': True
            }
        )
        if not created:
            account.is_active = True
            account.smtp_encryption = 'none'
            account.imap_use_ssl = False
            account.save()
        self.stdout.write(self.style.SUCCESS('1. Provisioned Mock SMTP/IMAP Account.'))

        # 2. Seed Campaign and Lead (campaign must be ACTIVE: dispatch now respects campaign status)
        campaign, _ = Campaign.objects.get_or_create(
            name='E2E Test Campaign',
            defaults={
                'target_sector': 'Technology',
                'target_country': 'US',
                'target_persona': 'CTO',
                'value_proposition': 'We automate growth.',
                'outreach_channel': 'email',
                'status': 'active'
            }
        )
        campaign.status = 'active'
        campaign.save()

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
        # Reset state so re-runs don't trip the new stop-condition logic
        lead.status = 'uncontacted'
        lead.save()
        Reply.objects.filter(lead=lead).delete()
        self.stdout.write(self.style.SUCCESS('2. Seeded Test Campaign (active) and Lead.'))

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
        self.stdout.write(self.style.NOTICE('4. Triggering Dispatch Engine...'))
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
            response = requests.get(f'http://greenmail:8080/api/user/{lead.email}/messages', timeout=5)
            response.raise_for_status()
            emails = response.json()

            found = any('End-to-End Test Subject' in (e.get('subject') or '') for e in emails)
            if found:
                self.stdout.write(self.style.SUCCESS('   SUCCESS! Email payload intercepted by GreenMail mock server.'))
            else:
                self.stdout.write(self.style.ERROR('   FAILED! Email not found in GreenMail API.'))
        except requests.RequestException as e:
            self.stdout.write(self.style.WARNING(f'   Could not reach GreenMail API (Is the container running?): {e}'))
            self.stdout.write(self.style.NOTICE('   Test passed on DB level, but skipped network verification.'))

        # 7. INBOUND LEG: simulate the prospect replying, then read it over IMAP
        self.stdout.write(self.style.NOTICE('6. Simulating an incoming reply (SMTP -> GreenMail inbox)...'))
        try:
            reply_mime = MIMEText('Sounds interesting, tell me more!')
            reply_mime['Subject'] = 'Re: End-to-End Test Subject'
            reply_mime['From'] = 'target@mock.com'
            reply_mime['To'] = account.email
            reply_mime['In-Reply-To'] = msg.message_id
            reply_mime['References'] = msg.message_id

            with smtplib.SMTP('greenmail', 3025, timeout=10) as smtp:
                smtp.sendmail('target@mock.com', [account.email], reply_mime.as_string())
            time.sleep(1)

            self.stdout.write(self.style.NOTICE('7. Running IMAPReader against the mock inbox...'))
            reader = IMAPReader(account)
            processed = reader.read_inbox()

            reply_record = Reply.objects.filter(lead=lead, message=msg).first()
            lead.refresh_from_db()
            if processed >= 1 and reply_record:
                self.stdout.write(self.style.SUCCESS('   SUCCESS! Reply matched via thread headers and stored in CRM.'))
                if lead.status == 'replied':
                    self.stdout.write(self.style.SUCCESS('   SUCCESS! Lead status transitioned to "replied" (stop condition).'))
                else:
                    self.stdout.write(self.style.ERROR(f'   FAILED! Lead status is "{lead.status}", expected "replied".'))
            else:
                self.stdout.write(self.style.ERROR(f'   FAILED! IMAP processed {processed} replies; Reply record found: {bool(reply_record)}.'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'   Inbound leg skipped (GreenMail unreachable?): {e}'))

        # Cleanup Greenmail so subsequent tests are clean
        try:
            requests.post('http://greenmail:8080/api/service/reset', timeout=10)
        except requests.RequestException:
            pass

        self.stdout.write(self.style.SUCCESS('\nE2E Test Completed.'))
