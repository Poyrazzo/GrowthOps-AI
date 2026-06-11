from django.core.management.base import BaseCommand
from crm.models import Lead, Campaign, Company


class Command(BaseCommand):
    help = 'Seeds test leads for the active campaign to test approval and sending flow.'

    def handle(self, *args, **options):
        campaign = Campaign.objects.filter(status='active').first()
        if not campaign:
            self.stdout.write(self.style.ERROR('No active campaign found'))
            return

        test_leads = [
            {
                'first_name': 'Ahmet',
                'last_name': 'Yılmaz',
                'email': 'ahmet.yilmaz@example.com',
                'title': 'English Teacher',
                'company': 'Istanbul Language Academy',
            },
            {
                'first_name': 'Fatma',
                'last_name': 'Kaya',
                'email': 'fatma.kaya@example.com',
                'title': 'HR Manager',
                'company': 'Tech Company Istanbul',
            },
            {
                'first_name': 'Mehmet',
                'last_name': 'Demir',
                'email': 'mehmet.demir@example.com',
                'title': 'Training Director',
                'company': 'Corporate Training Center',
            },
        ]

        for lead_data in test_leads:
            company, _ = Company.objects.get_or_create(
                name=lead_data['company'],
                defaults={'sector': 'Education & Training'}
            )

            lead, created = Lead.objects.get_or_create(
                email=lead_data['email'],
                defaults={
                    'first_name': lead_data['first_name'],
                    'last_name': lead_data['last_name'],
                    'title': lead_data['title'],
                    'company': company,
                    'campaign': campaign,
                    'status': 'uncontacted',
                    'lead_score': 85,
                }
            )

            status = 'Created' if created else 'Already exists'
            self.stdout.write(self.style.SUCCESS(
                f'{status}: {lead.first_name} {lead.last_name} ({lead.email})'
            ))

        self.stdout.write(self.style.SUCCESS(f'\n✓ Test leads seeded for campaign: {campaign.name}'))
