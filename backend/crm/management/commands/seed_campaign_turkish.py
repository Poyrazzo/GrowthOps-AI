from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from crm.models import Campaign, LeadSource


class Command(BaseCommand):
    help = 'Seeds a Turkish English language education campaign with lead sources.'

    def handle(self, *args, **options):
        # Create Campaign
        tomorrow = datetime.now().date() + timedelta(days=1)

        campaign, created = Campaign.objects.get_or_create(
            name='Konuşarak Öğren - English Speaking Product',
            defaults={
                'target_sector': 'English Language Education & Corporate Training',
                'target_country': 'Turkey',
                'target_persona': 'English Language Teachers, HR Managers, Training Directors',
                'value_proposition': (
                    'Konuşarak Öğren is an AI-powered English speaking practice platform that helps '
                    'students and professionals improve fluency through real-time conversation. '
                    'Perfect for language schools, universities, and corporate training programs.'
                ),
                'lead_magnet': 'Free 7-day trial',
                'outreach_channel': 'email',
                'success_metric': 'Trial signups and demo requests',
                'start_date': tomorrow,
                'end_date': tomorrow,
                'status': 'draft',
            }
        )

        status_msg = 'Created' if created else 'Already exists'
        self.stdout.write(self.style.SUCCESS(f'{status_msg}: Campaign "{campaign.name}"'))

        # Create Lead Sources
        sources = [
            {
                'url': 'https://www.universiteler.net/',
                'source_type': 'directory',
                'sector': 'Higher Education',
                'priority_score': 95,
            },
            {
                'url': 'https://www.egitim.gov.tr/',
                'source_type': 'directory',
                'sector': 'Education Ministry',
                'priority_score': 90,
            },
            {
                'url': 'https://www.dilkurslari.org/',
                'source_type': 'directory',
                'sector': 'Language Schools',
                'priority_score': 100,
            },
            {
                'url': 'https://www.akodemi.com/',
                'source_type': 'static',
                'sector': 'Language Education',
                'priority_score': 85,
            },
        ]

        for source_data in sources:
            source, created = LeadSource.objects.get_or_create(
                url=source_data['url'],
                defaults={
                    'source_type': source_data['source_type'],
                    'sector': source_data['sector'],
                    'priority_score': source_data['priority_score'],
                    'campaign': campaign,
                }
            )
            status_msg = 'Created' if created else 'Already exists'
            self.stdout.write(self.style.SUCCESS(f'{status_msg}: LeadSource "{source.url}"'))

        self.stdout.write(self.style.WARNING(
            '\n✓ Campaign and LeadSources seeded.\n'
            '→ Edit them in Django admin: http://localhost:18000/admin/crm/campaign/\n'
            '→ Change status to "active" in Phase F (Step 21) when ready to go live.'
        ))
