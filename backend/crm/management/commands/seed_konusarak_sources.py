from django.core.management.base import BaseCommand
from crm.models import Campaign, LeadSource

# ---------------------------------------------------------------------------
# SOURCE STRATEGY
# ---------------------------------------------------------------------------
# Konuşarak Öğren targets B2B decision-makers in the Turkish English-education
# market: school directors, corporate L&D managers, ELT coordinators, and
# professional English tutors.
#
# Source tiers:
#   TIER 1 (priority 90-100): Pages that list INDIVIDUAL STAFF with names+titles
#     → school team/kadromuz pages, tutor directories, association member lists
#   TIER 2 (priority 70-89): School contact/about pages with role inboxes
#     → still useful for company enrichment + pipeline entry
#   TIER 3 (priority 50-69): Marketplace/aggregator listings with tutor profiles
#     → directory mode: deep-crawls individual tutor profile pages
# ---------------------------------------------------------------------------

SOURCES = [

    # ── TIER 1: Staff / Team pages ──────────────────────────────────────────
    # These pages list individual instructors/directors by name — highest value.

    ("https://www.englishtime.com/egitmenlerimiz", "static", "Language School Staff", 98),
    ("https://www.englishtime.com/hakkimizda",     "static", "Language School Staff", 97),
    ("https://www.britishside.com/ekibimiz",       "static", "Language School Staff", 96),
    ("https://www.britishside.com/hakkimizda",     "static", "Language School Staff", 95),
    ("https://www.wallstreetenglish.com.tr/ekip",  "static", "Language School Staff", 94),
    ("https://www.americanlife.com.tr/kadromuz",   "static", "Language School Staff", 93),
    ("https://www.americanlife.com.tr/hakkimizda", "static", "Language School Staff", 92),
    ("https://www.kentingilizce.com/hakkimizda",   "static", "Language School Staff", 91),
    ("https://www.sistemdil.com/hakkimizda",       "static", "Language School Staff", 90),

    # ── TIER 1: Corporate training providers (staff/contact pages) ───────────
    ("https://www.tomer.com.tr/iletisim",          "static", "Corporate Language Training", 92),
    ("https://www.tomer.com.tr/hakkimizda",        "static", "Corporate Language Training", 91),
    ("https://www.dilmer.com/iletisim",             "static", "Language Training Institute", 89),
    ("https://www.dilmer.com/hakkimizda",           "static", "Language Training Institute", 88),
    ("https://www.dilko.com.tr/iletisim",           "static", "Language School",             87),
    ("https://www.dilko.com.tr/hakkimizda",         "static", "Language School",             86),
    ("https://www.dogusakademi.com/iletisim",       "static", "Language Academy",            85),
    ("https://www.bireyselders.com/ingilizce",      "static", "Private Tutoring",            83),

    # ── TIER 1: Association & professional network member directories ─────────
    # TÖMER affiliated schools, ELT associations
    ("https://www.ialf.edu/teachers",               "static", "ELT Professional Network",   96),
    ("https://iatefl.org.tr/uyeler",                "static", "ELT Association Members",    95),
    ("https://iatefl.org.tr/iletisim",              "static", "ELT Association",            90),

    # ── TIER 2: Language school contact pages (company inboxes — good for enrichment)
    ("https://www.englishtime.com/iletisim",        "static", "English Language School",    88),
    ("https://www.britishside.com/iletisim",        "static", "English Language School",    85),
    ("https://www.americanlife.com.tr/iletisim",    "static", "English Language School",    84),
    ("https://www.kentingilizce.com/iletisim",      "static", "English Language School",    83),
    ("https://www.sistemdil.com/iletisim",          "static", "Language School",            80),
    ("https://www.wallstreetenglish.com.tr/iletisim", "static", "Language School",          80),
    ("https://www.englishcenter.com.tr/iletisim",   "static", "English Language School",    78),
    ("https://www.englishcenter.com.tr/hakkimizda", "static", "English Language School",    77),
    ("https://amerikankulturu.com.tr/iletisim/",    "static", "Language School",            76),

    # ── TIER 3: Tutor marketplaces — directory mode → deep-crawls profiles ───
    # Each listing page contains individual tutor profiles with contact details.
    ("https://www.armut.com/ingilizce-dersi",            "directory", "Tutoring Marketplace",     95),
    ("https://www.superders.com/ingilizce-dersi",        "directory", "Tutoring Marketplace",     93),
    ("https://www.ozelders.com/ingilizce-dersi",         "directory", "Private Tutoring",         91),
    ("https://www.eodev.com/ogretmen/ingilizce",         "directory", "Online Tutor Directory",   89),
    ("https://www.dilkurslari.org/",                     "directory", "Language School Directory",88),
    ("https://www.kursrehberi.com/ingilizce-kurslari",   "directory", "Course Directory",         85),

    # ── TIER 3: Corporate HR / L&D directories ───────────────────────────────
    # Companies that buy corporate English training for employees
    ("https://www.yenibiris.com/is-ilanlari/egitim-kurumu", "directory", "HR/Training Job Listings", 80),
    ("https://www.kariyer.net/is-ilani?pozisyon=ingilizce-egitmen", "directory", "Job Listing Board", 78),
]
# LinkedIn is NOT listed here as explicit sources.
# When LINKEDIN_ENRICHMENT_ENABLED=true, the beat task automatically generates
# LinkedIn People search queries from campaign.target_persona and runs them —
# no manual sources needed.


class Command(BaseCommand):
    help = 'Seeds high-quality English-education lead sources into the Konuşarak Öğren campaign.'

    def add_arguments(self, parser):
        parser.add_argument('--campaign', type=str, default=None,
                            help='Campaign id or name fragment.')
        parser.add_argument('--clear', action='store_true',
                            help='Remove all existing sources before seeding.')

    def handle(self, *args, **options):
        camp_arg = options.get('campaign')
        if camp_arg:
            campaign = (Campaign.objects.filter(id=camp_arg).first()
                        or Campaign.objects.filter(name__icontains=camp_arg).first())
        else:
            campaign = (Campaign.objects.filter(name__icontains='Konuşarak')
                        .exclude(name__icontains='E2E')
                        .exclude(name__icontains='Test')
                        .order_by('created_at').first())

        if not campaign:
            self.stdout.write(self.style.ERROR(
                'Campaign not found. Pass --campaign "<id or name>".'))
            return

        if options['clear']:
            removed = LeadSource.objects.filter(campaign=campaign).delete()
            self.stdout.write(self.style.WARNING(
                f'Cleared {removed[0]} existing sources from "{campaign.name}"'))

        created, updated, skipped = 0, 0, 0
        for url, source_type, sector, priority in SOURCES:
            obj, was_created = LeadSource.objects.get_or_create(
                url=url,
                defaults={
                    'source_type': source_type,
                    'sector': sector,
                    'priority_score': priority,
                    'campaign': campaign,
                    'last_scraped_at': None,
                }
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'+ [{source_type:10}] {url}'))
            else:
                # Re-link orphaned or update priority if changed
                changed = False
                if obj.campaign_id != campaign.id:
                    obj.campaign = campaign
                    changed = True
                if obj.priority_score != priority:
                    obj.priority_score = priority
                    changed = True
                if obj.source_type != source_type:
                    obj.source_type = source_type
                    changed = True
                if changed:
                    obj.last_scraped_at = None   # force re-scrape
                    obj.save()
                    updated += 1
                    self.stdout.write(self.style.WARNING(f'~ [{source_type:10}] {url}'))
                else:
                    skipped += 1
                    self.stdout.write(f'= [{source_type:10}] {url}')

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. {created} new | {updated} updated | {skipped} unchanged. '
            f'"{campaign.name}" now has {campaign.sources.count()} sources.'))
