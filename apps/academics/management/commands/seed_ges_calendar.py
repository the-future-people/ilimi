from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.academics.models import GESCalendarTemplate, GESCalendarTermTemplate


# Transcribed from GES press releases signed by Daniel Fenyi,
# Head of Public Relations, Ghana Education Service.
# Re-run this command after each May release to add the new year.
CALENDARS = [
    {
        'name': '2025/2026',
        'start_date': date(2025, 9, 2),
        'end_date': date(2026, 7, 24),
        'exam_start_date': date(2026, 5, 4),
        'exam_end_date': date(2026, 5, 11),
        'published_on': date(2025, 7, 12),
        'source_note': 'GES press release, 12 July 2025 (BECE 4-11 May 2026)',
        'terms': [
            {
                'name': 'term_1',
                'start_date': date(2025, 9, 2),
                'end_date': date(2025, 12, 18),
                'vacation_start_date': date(2025, 12, 19),
                'vacation_end_date': date(2026, 1, 7),
                'midterm_start_date': date(2025, 10, 31),
                'midterm_end_date': date(2025, 11, 3),
            },
            {
                'name': 'term_2',
                'start_date': date(2026, 1, 8),
                'end_date': date(2026, 4, 1),
                'vacation_start_date': date(2026, 4, 2),
                'vacation_end_date': date(2026, 4, 20),
                'midterm_start_date': None,
                'midterm_end_date': None,
            },
            {
                'name': 'term_3',
                'start_date': date(2026, 4, 21),
                'end_date': date(2026, 7, 23),
                'vacation_start_date': date(2026, 7, 24),
                'vacation_end_date': None,
                'midterm_start_date': None,
                'midterm_end_date': None,
            },
        ],
    },
    {
        'name': '2026/2027',
        'start_date': date(2026, 9, 8),
        'end_date': date(2027, 7, 23),
        'exam_start_date': date(2027, 5, 5),
        'exam_end_date': date(2027, 5, 12),
        'published_on': date(2026, 5, 6),
        'source_note': 'GES press release, 6 May 2026 (BECE 5-12 May 2027)',
        'terms': [
            {
                'name': 'term_1',
                'start_date': date(2026, 9, 8),
                'end_date': date(2026, 12, 17),
                'vacation_start_date': date(2026, 12, 18),
                'vacation_end_date': date(2027, 1, 4),
                'midterm_start_date': date(2026, 11, 5),
                'midterm_end_date': date(2026, 11, 6),
            },
            {
                'name': 'term_2',
                'start_date': date(2027, 1, 5),
                'end_date': date(2027, 3, 25),
                'vacation_start_date': date(2027, 3, 26),
                'vacation_end_date': date(2027, 4, 19),
                'midterm_start_date': None,
                'midterm_end_date': None,
            },
            {
                'name': 'term_3',
                'start_date': date(2027, 4, 20),
                'end_date': date(2027, 7, 22),
                'vacation_start_date': date(2027, 7, 23),
                'vacation_end_date': None,
                'midterm_start_date': None,
                'midterm_end_date': None,
            },
        ],
    },
]


class Command(BaseCommand):
    help = (
        "Seed or refresh the global GES academic calendar templates. "
        "Idempotent - safe to re-run."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for source in CALENDARS:
            entry = dict(source)
            terms = entry.pop('terms')
            name = entry.pop('name')

            calendar, created = GESCalendarTemplate.objects.update_or_create(
                name=name,
                defaults=entry,
            )

            for term in terms:
                GESCalendarTermTemplate.objects.update_or_create(
                    calendar=calendar,
                    name=term['name'],
                    defaults={k: v for k, v in term.items() if k != 'name'},
                )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f"  Created GES {name} ({len(terms)} terms)"
                ))
            else:
                updated_count += 1
                self.stdout.write(
                    f"  Refreshed GES {name} ({len(terms)} terms)"
                )

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {created_count} created, {updated_count} refreshed."
        ))