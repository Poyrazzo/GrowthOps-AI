from django.core.management.base import BaseCommand
from crm.models import Campaign, LeadSource


# Real Turkish English-education-related sites and directories. Contact/about
# pages tend to expose role inboxes (info@, iletisim@) and sometimes staff
# emails — exactly the lead surface this campaign targets.
SOURCES = [
    # Language schools — contact pages
    ("https://www.englishtime.com/iletisim", "static", "English Language School", 90),
    ("https://amerikankulturu.com.tr/iletisim/", "static", "English Language School", 88),
    ("https://www.britishside.com/iletisim", "static", "English Language School", 85),
    ("https://www.wallstreetenglish.com.tr/iletisim", "static", "English Language School", 85),
    ("https://www.kentingilizce.com/iletisim", "static", "English Language School", 80),
    ("https://www.sistemdil.com/iletisim", "static", "Language School", 78),
    ("https://www.englishcenter.com.tr/iletisim", "static", "English Language School", 78),
    ("https://www.americanlife.com.tr/iletisim", "static", "English Language School", 80),
    # Education / tutoring portals and directories
    ("https://www.dilkurslari.org/", "directory", "Language School Directory", 95),
    ("https://www.kursrehberi.com/ingilizce-kurslari", "directory", "Course Directory", 82),
    ("https://www.armut.com/ingilizce-dersi", "directory", "Tutoring Marketplace", 80),
    # Universities (language prep schools / hazirlik) — staff & dept contacts
    ("https://ydyo.aydin.edu.tr/iletisim/", "static", "University Prep School", 75),
    ("https://sfl.bilkent.edu.tr/contact/", "static", "University Prep School", 75),
    ("https://ingilizce.bogazici.edu.tr", "static", "University English Dept", 72),
    # Corporate / professional training providers
    ("https://www.cambridgeenglish.org.tr/iletisim", "static", "Corporate Training", 70),
    ("https://www.speexx.com/tr/iletisim/", "static", "Corporate Language Training", 70),
]


class Command(BaseCommand):
    help = 'Adds a broad set of real English-education lead sources to the Konuşarak Öğren campaign.'

    def add_arguments(self, parser):
        parser.add_argument('--campaign', type=str, default=None,
                            help='Campaign id or name fragment. Defaults to the Konuşarak Öğren campaign.')

    def handle(self, *args, **options):
        camp_arg = options.get('campaign')
        if camp_arg:
            campaign = (Campaign.objects.filter(id=camp_arg).first()
                        or Campaign.objects.filter(name__icontains=camp_arg).first())
        else:
            # Prefer the real product campaign, not any "E2E"/"Test" verification one.
            campaign = (Campaign.objects.filter(name__icontains='Konuşarak')
                        .exclude(name__icontains='E2E')
                        .exclude(name__icontains='Test')
                        .order_by('created_at').first())

        if not campaign:
            self.stdout.write(self.style.ERROR(
                'Campaign not found. Pass --campaign "<id or name>".'))
            return

        created, skipped = 0, 0
        for url, source_type, sector, priority in SOURCES:
            obj, was_created = LeadSource.objects.get_or_create(
                url=url,
                defaults={
                    'source_type': source_type,
                    'sector': sector,
                    'priority_score': priority,
                    'campaign': campaign,
                }
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'+ {url}'))
            else:
                # Re-point an existing source at this campaign if it was orphaned
                if obj.campaign_id != campaign.id:
                    obj.campaign = campaign
                    obj.save(update_fields=['campaign'])
                    self.stdout.write(self.style.WARNING(f'~ re-linked {url}'))
                else:
                    self.stdout.write(f'= exists {url}')
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. {created} new sources added, {skipped} already present. '
            f'Campaign "{campaign.name}" now has {campaign.sources.count()} sources.'))
