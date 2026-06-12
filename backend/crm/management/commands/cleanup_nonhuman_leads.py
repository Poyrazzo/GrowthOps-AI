from django.core.management.base import BaseCommand
from django.db.models import Q

from crm.models import Lead


class Command(BaseCommand):
    help = 'Find or delete low-confidence non-human leads such as branch/company inboxes.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete matching leads. Without this flag, the command is dry-run only.',
        )

    def handle(self, *args, **options):
        nonhuman = (
            Lead.objects
            .filter(email__isnull=False, linkedin_url__isnull=True, profile_url__isnull=True)
            .filter(Q(is_generic_email=True) | (
                (Q(last_name__isnull=True) | Q(last_name='')) &
                (Q(title__isnull=True) | Q(title=''))
            ))
            .exclude(status__in=['in_sequence', 'replied'])
        )

        count = nonhuman.count()
        sample = list(nonhuman.values_list('email', flat=True)[:20])

        if not options['delete']:
            self.stdout.write(self.style.WARNING(
                f'Dry run: {count} non-human lead candidates found.'
            ))
            for email in sample:
                self.stdout.write(f'  - {email}')
            self.stdout.write('\nRun again with --delete to remove them.')
            return

        deleted, _ = nonhuman.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {deleted} non-human lead rows.'))
