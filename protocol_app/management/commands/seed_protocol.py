# protocol_app/management/commands/seed_protocol.py
"""
Management command: python manage.py seed_protocol
Seeds the database with:
  - 10 elite motivation quotes
  - 30 days of sample DailyReport data for the superuser
"""
import random
import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from protocol_app.models import MotivationQuote, DailyReport


QUOTES = [
    {
        'text': 'The man who moves a mountain begins by carrying away small stones.',
        'font_style': 'playfair',
    },
    {
        'text': 'Discipline is the bridge between goals and accomplishment.',
        'font_style': 'orbitron',
    },
    {
        'text': 'Do not wait for the perfect moment. Take the moment and make it perfect.',
        'font_style': 'playfair',
    },
    {
        'text': 'You are what you repeatedly do. Excellence is not an act, but a habit.',
        'font_style': 'serif',
    },
    {
        'text': 'The Protocol does not care about your feelings. It cares about your actions.',
        'font_style': 'orbitron',
    },
    {
        'text': 'Pain is temporary. The data you log today compounds forever.',
        'font_style': 'playfair',
    },
    {
        'text': 'Every champion was once a beginner who refused to stay one.',
        'font_style': 'serif',
    },
    {
        'text': 'Iron sharpens iron. The Protocol sharpens you.',
        'font_style': 'orbitron',
    },
    {
        'text': 'There is no traffic on the extra mile.',
        'font_style': 'playfair',
    },
    {
        'text': 'You do not rise to the level of your goals. You fall to the level of your systems.',
        'font_style': 'serif',
    },
]


class Command(BaseCommand):
    help = 'Seeds the Protocol database with quotes and sample reports.'

    def handle(self, *args, **options):
        self.stdout.write('\n⬡ PROTOCOL SEED SEQUENCE INITIATED...\n')

        # ── Quotes ────────────────────────────────────────────────────────────
        created_quotes = 0
        for q in QUOTES:
            obj, created = MotivationQuote.objects.get_or_create(
                text=q['text'],
                defaults={
                    'font_style': q['font_style'],
                    'is_active':  True,
                }
            )
            if created:
                created_quotes += 1

        self.stdout.write(
            self.style.SUCCESS(f'  ✓ {created_quotes} quotes seeded ({len(QUOTES) - created_quotes} already existed)')
        )

        # ── Sample Reports (superuser) ────────────────────────────────────────
        try:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                self.stdout.write(
                    self.style.WARNING('  ⚠ No superuser found. Run createsuperuser first.')
                )
                return

            today         = timezone.localdate()
            created_rep   = 0
            skipped_rep   = 0

            for days_ago in range(30, 0, -1):
                report_date = today - datetime.timedelta(days=days_ago)

                # Skip some days randomly to simulate realistic gaps
                if random.random() < 0.15:
                    continue

                # Generate realistic-looking data with variance
                it_hours  = round(random.uniform(1.0, 7.0), 1)
                pages     = random.randint(0, 80)
                calories  = random.randint(0, 800)
                distance  = round(random.uniform(0.0, 10.0), 1)

                # Occasionally simulate a bad day (Relentless Penalty trigger)
                if random.random() < 0.1:
                    pages    = 0
                if random.random() < 0.08:
                    it_hours = 0.0

                obj, created = DailyReport.objects.get_or_create(
                    user=user,
                    date=report_date,
                    defaults={
                        'it_math_hours': it_hours,
                        'pages_read':    pages,
                        'calories':      calories,
                        'distance_km':   distance,
                        'ai_comment':    '',
                    }
                )

                if created:
                    # Force AI comment generation
                    obj.ai_comment = obj.generate_ai_comment()
                    obj.save()
                    created_rep += 1
                else:
                    skipped_rep += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f'  ✓ {created_rep} sample reports seeded for "{user.username}" '
                    f'({skipped_rep} already existed)'
                )
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Report seeding failed: {e}'))

        self.stdout.write('\n⬡ PROTOCOL SEED COMPLETE. SYSTEM READY.\n')