"""
Academic year and class level setup.

Business logic for standing up a brand-new school's academic structure:
resolving which GES calendar and term a school should start on, creating
the AcademicYear plus its three Terms atomically, and get-or-creating
ClassLevels on demand.
"""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.academics.models import (
    AcademicYear,
    ClassLevel,
    GESCalendarTemplate,
    Term,
)

# How close to a term/year ending before we assume the school means the
# *next* one. A school onboarding in the final fortnight is almost always
# preparing for what comes next, not joining what's ending.
ROLLOVER_WINDOW = timedelta(weeks=2)

TERM_SEQUENCE = ['term_1', 'term_2', 'term_3']


def suggest_calendar_and_term(today=None):
    """
    Recommend which GES calendar year and starting term to pre-select.

    This is a *suggestion only* — the setup form shows both as editable
    fields. Intent is not derivable from the calendar (a school in the last
    week of Term 2 may well be onboarding to begin in Term 3), so the user
    always gets the final say.

    Returns (template_or_None, term_name_or_None).
    """
    today = today or timezone.localdate()
    templates = list(
        GESCalendarTemplate.objects.filter(is_active=True).order_by('start_date')
    )
    if not templates:
        return None, None

    # Pick the year: the one containing today, unless it's nearly over.
    chosen = None
    for template in templates:
        if today > template.end_date:
            continue
        if today >= template.start_date and today > template.end_date - ROLLOVER_WINDOW:
            continue  # this year is ending — fall through to the next
        chosen = template
        break

    if chosen is None:
        chosen = templates[-1]

    # If we landed on a future year, the school starts at its beginning.
    if today < chosen.start_date:
        return chosen, 'term_1'

    return chosen, _suggest_term(chosen, today)


def _suggest_term(template, today):
    """Term containing today, rolled forward if that term is nearly over."""
    terms = {t.name: t for t in template.terms.all()}

    for index, name in enumerate(TERM_SEQUENCE):
        term = terms.get(name)
        if term is None:
            continue

        if today < term.start_date:
            return name  # in a vacation gap — next term up

        if today <= term.end_date:
            nearly_over = today > term.end_date - ROLLOVER_WINDOW
            if nearly_over and index + 1 < len(TERM_SEQUENCE):
                return TERM_SEQUENCE[index + 1]
            return name

    return TERM_SEQUENCE[-1]


@transaction.atomic
def create_academic_year_with_terms(
    school,
    name,
    start_date,
    end_date,
    terms,
    current_term_name='term_1',
):
    """
    Create a school's AcademicYear and its Terms in one atomic operation.

    `terms` is a list of dicts: {'name', 'start_date', 'end_date'}.
    All three terms are always created with their real dates — fees, report
    cards and CA scores all reference terms that aren't current. Only the
    `is_current` pointer reflects where the school is actually starting.

    Raises ValidationError on invalid input. Returns the AcademicYear.
    """
    if not terms:
        raise ValidationError("At least one term is required.")

    if start_date >= end_date:
        raise ValidationError("Academic year must end after it starts.")

    seen = set()
    for term in terms:
        term_name = term.get('name')
        if term_name not in TERM_SEQUENCE:
            raise ValidationError(f"Unknown term: {term_name!r}")
        if term_name in seen:
            raise ValidationError(f"Duplicate term: {term_name!r}")
        seen.add(term_name)

        if term['start_date'] >= term['end_date']:
            raise ValidationError(
                f"{term_name}: term must end after it starts."
            )

    if current_term_name not in seen:
        raise ValidationError(
            f"Starting term {current_term_name!r} is not among the terms provided."
        )

    if AcademicYear.objects.filter(school=school, name=name).exists():
        raise ValidationError(f"'{name}' already exists for this school.")

    year = AcademicYear.objects.create(
        school=school,
        name=name,
        start_date=start_date,
        end_date=end_date,
        is_current=True,
    )

    for term in sorted(terms, key=lambda t: TERM_SEQUENCE.index(t['name'])):
        Term.objects.create(
            academic_year=year,
            name=term['name'],
            start_date=term['start_date'],
            end_date=term['end_date'],
            is_current=(term['name'] == current_term_name),
        )

    return year


@transaction.atomic
def create_academic_year_from_template(school, template, current_term_name=None):
    """
    Convenience wrapper: stand up a school's year straight from a GES template.

    Used for the zero-friction path where a school accepts the published GES
    dates unedited. Any edits go through create_academic_year_with_terms
    directly with the school's own values.
    """
    template_terms = list(template.terms.all())
    if not template_terms:
        raise ValidationError(
            f"GES template '{template.name}' has no terms configured."
        )

    if current_term_name is None:
        current_term_name = _suggest_term(template, timezone.localdate())

    return create_academic_year_with_terms(
        school=school,
        name=template.name,
        start_date=template.start_date,
        end_date=template.end_date,
        terms=[
            {
                'name': t.name,
                'start_date': t.start_date,
                'end_date': t.end_date,
            }
            for t in template_terms
        ],
        current_term_name=current_term_name,
    )


def get_or_create_class_level(school, level_name):
    """
    Resolve a ClassLevel for a school, creating it on first use.

    Mirrors the Occupation/Position pattern. Order is auto-derived by
    ClassLevel.save(), so callers never set it.
    """
    valid = {choice[0] for choice in ClassLevel.LEVEL_CHOICES}
    if level_name not in valid:
        raise ValidationError(f"Unknown class level: {level_name!r}")

    level, _ = ClassLevel.objects.get_or_create(
        school=school,
        name=level_name,
    )
    return level