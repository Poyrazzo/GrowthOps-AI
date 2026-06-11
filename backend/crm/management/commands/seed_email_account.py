import os
from django.core.management.base import BaseCommand
from crm.models import EmailAccount


class Command(BaseCommand):
    help = 'Seeds the outreach Gmail account from OUTREACH_EMAIL / OUTREACH_APP_PASSWORD env vars.'

    def handle(self, *args, **options):
        email = os.environ.get('OUTREACH_EMAIL')
        password = os.environ.get('OUTREACH_APP_PASSWORD')

        if not email or not password:
            self.stdout.write(self.style.ERROR(
                'Set OUTREACH_EMAIL and OUTREACH_APP_PASSWORD in your .env before running this command.'
            ))
            return

        account, created = EmailAccount.objects.get_or_create(
            email=email,
            defaults={
                'username': email,
                'provider': 'gmail',
                'smtp_host': 'smtp.gmail.com',
                'smtp_port': 587,
                'smtp_encryption': 'tls',
                'imap_host': 'imap.gmail.com',
                'imap_port': 993,
                'imap_use_ssl': True,
                'daily_limit': 15,
                'is_active': True,
            }
        )

        if created:
            # Trigger the model's auto-encrypt on save
            account.password_encrypted = password
            account.save()
            self.stdout.write(self.style.SUCCESS(f'Created EmailAccount for {email}'))
        else:
            self.stdout.write(self.style.WARNING(f'EmailAccount for {email} already exists — skipped.'))
