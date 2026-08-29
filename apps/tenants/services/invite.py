import logging
import secrets
import string
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.tenants.models import SchoolMember, Branch
from apps.notifications.services.sms import send_sms

logger = logging.getLogger(__name__)

User = get_user_model()


def _generate_temp_password(length=12):
    """Generate a secure temporary password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@transaction.atomic
def invite_member(school, invited_by, data):
    """
    Invite a staff member to a school.

    Flow:
    - If user with email exists → link them to the school
    - If not → create inactive user with temp password → link → notify

    Returns dict with message and member details.
    """
    email = data['email']
    role = data['role']
    branch_id = data.get('branch_id')

    # Resolve branch if provided
    branch = None
    if branch_id:
        try:
            branch = Branch.objects.get(pk=branch_id, school=school)
        except Branch.DoesNotExist:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"branch_id": "Branch not found in your school."})

    # Check for duplicate membership
    existing_user = User.objects.filter(email=email).first()
    if existing_user:
        already_member = SchoolMember.objects.filter(
            user=existing_user, school=school
        ).exists()
        if already_member:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"email": "This person is already a member of your school."})

    if existing_user:
        # User exists on platform — just link them
        member = SchoolMember.objects.create(
            user=existing_user,
            school=school,
            branch=branch,
            role=role,
            role_ref=_resolve_role(school, role),
            is_active=True,
        )
        _notify_existing_user(existing_user, school, role, invited_by)
        logger.info(f"Existing user {email} added to {school.name} as {role}")
        return {
            "message": f"{existing_user.first_name} has been added to {school.name}.",
            "member_id": member.id,
            "is_new_user": False,
        }

    else:
        # New user — create account with temp password
        temp_password = _generate_temp_password()
        new_user = User.objects.create_user(
            email=email,
            password=temp_password,
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            phone_number=data.get('phone_number', ''),
            is_active=True,
        )
        member = SchoolMember.objects.create(
            user=new_user,
            school=school,
            branch=branch,
            role=role,
            role_ref=_resolve_role(school, role),
            is_active=True,
        )
        _notify_new_user(new_user, school, role, temp_password, invited_by)
        logger.info(f"New user {email} created and added to {school.name} as {role}")
        return {
            "message": f"Invitation sent to {email}. They will receive their login details.",
            "member_id": member.id,
            "is_new_user": True,
        }


def _resolve_role(school, slug):
    """
    The school's role for this slug, seeding defaults if the school has
    none yet. Falls back to teacher rather than leaving someone with no
    permissions at all.
    """
    from apps.tenants.models import SchoolRole
    from apps.tenants.services.roles import seed_default_roles

    role = SchoolRole.objects.filter(school=school, slug=slug).first()
    if role:
        return role

    seed_default_roles(school)
    return (
        SchoolRole.objects.filter(school=school, slug=slug).first()
        or SchoolRole.objects.filter(school=school, slug='teacher').first()
    )


def _notify_existing_user(user, school, role, invited_by):
    """Notify an existing platform user they've been added to a school."""
    resolved = _resolve_role(school, role)
    role_display = resolved.name if resolved else role
    message = (
        f"Hi {user.first_name}, you have been added to {school.name} "
        f"as {role_display} by {invited_by.full_name}. "
        f"Log in at ilimi.app to get started."
    )
    if user.phone_number:
        try:
            send_sms(user.phone_number, message)
        except Exception as e:
            logger.warning(f"Failed to notify existing user {user.email}: {e}")


def _notify_new_user(user, school, role, temp_password, invited_by):
    """Send login credentials to a newly invited user via SMS."""
    message = (
        f"Hi {user.first_name or 'there'}, you have been invited to join {school.name} "
        f"on Ilimi as {role}. "
        f"Login: {user.email} | Temp password: {temp_password} "
        f"Please change your password after first login."
    )
    if user.phone_number:
        try:
            send_sms(user.phone_number, message)
        except Exception as e:
            logger.warning(f"Failed to notify new user {user.email}: {e}")
    else:
        # No phone number — log credentials for dev visibility
        logger.info(
            f"\n{'='*50}\n"
            f"INVITE (no phone)\n"
            f"Email: {user.email}\n"
            f"Temp password: {temp_password}\n"
            f"School: {school.name} | Role: {role}\n"
            f"{'='*50}"
        )