import logging
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from apps.tenants.models import School, Branch, SchoolMember, SubscriptionPlan, SchoolRole
from apps.tenants.services.roles import seed_default_roles
from apps.notifications.services.sms import send_welcome_sms
from apps.tenants.models.role import SchoolRole
from apps.tenants.services.roles import seed_default_roles

logger = logging.getLogger(__name__)


@transaction.atomic
def create_school_with_owner(user, school_data):
    """
    Create a school, its default Main Campus branch, and link the user
    as school_admin. Called after phone verification succeeds during
    registration. Marks onboarding as complete and sends a welcome SMS.
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
        onboarding_complete=True,
        onboarding_step=2,
    )

    seed_default_roles(school)

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

        # The person registering the school is running it, not merely
    # overseeing it, so they start as assistant head. A genuine owner who
    # delegates day-to-day work is moved to proprietor afterwards.
    owner_role = SchoolRole.objects.get(school=school, slug='assistant_head')

    SchoolMember.objects.create(
        user=user,
        school=school,
        branch=branch,
        role='school_admin',
        role_ref=owner_role,
        position_title=school_data.get('position_title', ''),
        is_active=True,
    )

    send_welcome_sms(user.phone_number, school.name)

    logger.info(f"School created with main branch: {school.name} by {user.email}")
    return school