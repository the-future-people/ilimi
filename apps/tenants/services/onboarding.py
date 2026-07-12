import logging
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from apps.tenants.models import School, Branch, SchoolMember, SubscriptionPlan
from apps.notifications.services.sms import send_welcome_sms

logger = logging.getLogger(__name__)


@transaction.atomic
def create_school_with_owner(user, school_data):
    """
    Create a school, its default Main Campus branch, and link the user
    as school_admin. Called after step 2 of registration. Marks
    onboarding as complete and sends a welcome SMS.
    Returns the created School instance.
    """
    free_plan = SubscriptionPlan.objects.filter(plan_type='free').first()

    school = School.objects.create(
        name=school_data['school_name'],
        email=school_data['school_email'],
        phone=school_data['school_phone'],
        city=school_data['city'],
        country=school_data.get('country', 'Ghana'),
        school_type=school_data.get('school_type', ''),
        expected_student_count=school_data.get('expected_student_count', ''),
        subscription_plan=free_plan,
        subscription_status='trial',
        trial_ends_at=timezone.now() + timedelta(days=30),
        onboarding_complete=False,
        onboarding_step=1,
    )

    if school_data.get('logo'):
        school.logo = school_data['logo']
        school.save(update_fields=['logo'])

    branch = Branch.objects.create(
        school=school,
        name='Main Campus',
        branch_code='MAIN',
        address=school_data.get('address', ''),
        city=school.city,
        phone=school.phone,
        email=school.email,
        is_main_branch=True,
        is_active=True,
    )

    SchoolMember.objects.create(
        user=user,
        school=school,
        branch=branch,
        role='school_admin',
        position_title=school_data.get('position_title', ''),
        is_active=True,
    )

    school.onboarding_complete = True
    school.onboarding_step = 2
    school.save(update_fields=['onboarding_complete', 'onboarding_step'])

    send_welcome_sms(user.phone_number, school.name)

    logger.info(f"School created with main branch: {school.name} by {user.email}")
    return school


@transaction.atomic
def create_main_branch(school, branch_data):
    """
    Create the main branch for a school during onboarding.
    Returns the created Branch instance.
    """
    branch = Branch.objects.create(
        school=school,
        name=branch_data['branch_name'],
        branch_code=branch_data.get('branch_code', 'MAIN'),
        address=branch_data['address'],
        city=branch_data.get('city', school.city),
        phone=branch_data.get('phone', school.phone),
        email=branch_data.get('email', school.email),
        is_main_branch=True,
        is_active=True,
    )

    logger.info(f"Main branch created: {branch.name} for {school.name}")
    return branch


@transaction.atomic
def complete_onboarding(school, user):
    """
    Mark onboarding as complete and send welcome SMS.
    """
    school.onboarding_complete = True
    school.onboarding_step = 3
    school.save(update_fields=['onboarding_complete', 'onboarding_step'])

    send_welcome_sms(user.phone_number, school.name)
    logger.info(f"Onboarding completed for school: {school.name}")