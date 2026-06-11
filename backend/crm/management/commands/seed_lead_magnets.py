from django.core.management.base import BaseCommand
from crm.models import LeadMagnet


class Command(BaseCommand):
    help = 'Seeds example lead magnets for testing.'

    def handle(self, *args, **options):
        magnets = [
            {
                'name': 'Growth Strategy Guide',
                'description': 'Free guide on scaling your business. Use with founders and growth-stage CEOs.',
                'url': 'https://example.com/growth-strategy-guide',
                'target_persona': 'Founder, CEO, Growth Manager',
            },
            {
                'name': 'ROI Calculator',
                'description': 'Interactive tool to calculate outreach ROI. Best for marketing and sales leaders.',
                'url': 'https://example.com/roi-calculator',
                'target_persona': 'CMO, Sales Director, Marketing Manager',
            },
            {
                'name': 'AI Automation Checklist',
                'description': '10-point checklist for automating sales workflows. Target: operations and sales enablement.',
                'url': 'https://example.com/automation-checklist',
                'target_persona': 'Sales Ops Manager, RevOps Lead',
            },
        ]

        for data in magnets:
            magnet, created = LeadMagnet.objects.get_or_create(
                name=data['name'],
                defaults={
                    'description': data['description'],
                    'url': data['url'],
                    'target_persona': data['target_persona'],
                }
            )
            status = 'Created' if created else 'Already exists'
            self.stdout.write(self.style.SUCCESS(f'{status}: {magnet.name}'))
