from django.db import transaction
from django.utils import timezone


DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']


def create_lesson_plan(school, classroom, subject, term, week_ending,
                       facilitator, branch=None, **fields):
    """
    Creates a week's plan with its five day rows ready to fill.
    Days left blank simply mean nothing was taught that day.
    """
    from apps.academics.models import LessonPlan, LessonPlanDay

    with transaction.atomic():
        plan = LessonPlan.objects.create(
            school=school,
            branch=branch,
            classroom=classroom,
            subject=subject,
            term=term,
            week_ending=week_ending,
            facilitator=facilitator,
            **fields,
        )
        LessonPlanDay.objects.bulk_create([
            LessonPlanDay(plan=plan, day=d, order=i)
            for i, d in enumerate(DAYS)
        ])

    return plan


def submit_lesson_plan(plan, member):
    """Teacher hands the week in for vetting."""
    if plan.facilitator_id and plan.facilitator_id != member.id:
        raise ValueError("Only the facilitator who wrote this plan can submit it.")
    if plan.status == 'submitted':
        raise ValueError("This plan has already been submitted.")
    if plan.status == 'vetted':
        raise ValueError("This plan has been vetted and cannot be resubmitted.")

    if not plan.days.filter(phase_2_main__gt='').exists():
        raise ValueError("Write at least one day's lesson before submitting.")

    plan.status = 'submitted'
    plan.submitted_at = timezone.now()
    plan.save(update_fields=['status', 'submitted_at'])
    return plan


def vet_lesson_plan(plan, member, approved, remarks=''):
    """
    Head of academics approves or returns a submitted plan.
    Admin-tier does the same for the head of academics' own plans.
    """
    from apps.tenants.permissions import can_vet_plan
    from apps.notifications.models import Notification

    if not can_vet_plan(member, plan):
        raise PermissionError("You cannot vet this lesson plan.")

    if plan.status != 'submitted':
        raise ValueError("Only submitted plans can be vetted.")

    if not approved and not remarks.strip():
        raise ValueError("Say what needs changing when returning a plan.")

    plan.status = 'vetted' if approved else 'returned'
    plan.vetted_by = member
    plan.vetted_at = timezone.now()
    plan.vetting_remarks = remarks.strip()
    plan.save(update_fields=['status', 'vetted_by', 'vetted_at', 'vetting_remarks'])

    if plan.facilitator and plan.facilitator.user:
        Notification.objects.create(
            school=plan.school,
            recipient=plan.facilitator.user,
            title='Lesson plan vetted' if approved else 'Lesson plan returned',
            message=(
                f"{plan.subject} for {plan.classroom}, week ending {plan.week_ending}, "
                + ('has been vetted.' if approved else f'needs revision: {remarks.strip()}')
            ),
        )

    return plan