import logging
from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import User, PendingRegistration
from apps.notifications.services.sms import send_otp_sms, send_welcome_sms

logger = logging.getLogger(__name__)


def start_registration(data):
    """
    Creates a PendingRegistration holding all collected school + personal
    data, plus a fresh OTP, and sends it. No real User/School exists yet —
    only verify_and_create() creates real records, atomically, on success.
    Returns the created PendingRegistration.
    """
    # Clear out any previous pending attempt for this email/phone so
    # someone retrying doesn't accumulate multiple stale rows.
    PendingRegistration.objects.filter(email=data['email']).delete()
    PendingRegistration.objects.filter(phone_number=data['phone_number']).delete()

    pending = PendingRegistration.objects.create(
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=data['email'],
        phone_number=data['phone_number'],
        password_hash=make_password(data['password']),
        position_title=data.get('position_title', ''),
        school_name=data['school_name'],
        school_email=data.get('school_email', ''),
        school_phone=data.get('school_phone', ''),
        city=data['city'],
        country=data.get('country', 'Ghana'),
        school_type=data.get('school_type', ''),
        expected_student_count=data.get('expected_student_count', ''),
    )

    send_otp_sms(pending.phone_number, pending.otp)
    logger.info(f"Registration started (pending): {pending.email} — {pending.school_name}")
    return pending


def resend_pending_otp(pending):
    """
    Regenerate and resend the OTP for a pending registration.
    Rate limited — once per minute.
    Returns (success, message).
    """
    time_since_creation = timezone.now() - pending.otp_created_at
    if time_since_creation < timedelta(minutes=1):
        seconds_left = 60 - int(time_since_creation.total_seconds())
        return False, f'Please wait {seconds_left} seconds before requesting a new code.'

    otp = pending.regenerate_otp()
    send_otp_sms(pending.phone_number, otp)
    return True, 'A new verification code has been sent to your phone.'


@transaction.atomic
def verify_and_create(pending, code):
    """
    Verifies the OTP on a PendingRegistration. On success, atomically
    creates the real User, School, Branch, and SchoolMember, deletes the
    pending row, and returns the new User ready for login/token issuance.
    Returns (success, message, user_or_none).
    """
    success, message = pending.verify(code)
    if not success:
        return False, message, None

    from apps.tenants.services.onboarding import create_school_with_owner

    user = User.objects.create(
        email=pending.email,
        password=pending.password_hash,
        first_name=pending.first_name,
        last_name=pending.last_name,
        phone_number=pending.phone_number,
        is_active=True,
        is_phone_verified=True,
    )

    school_data = {
        'school_name': pending.school_name,
        'school_email': pending.school_email or pending.email,
        'school_phone': pending.school_phone or pending.phone_number,
        'city': pending.city,
        'country': pending.country,
        'school_type': pending.school_type,
        'expected_student_count': pending.expected_student_count,
        'position_title': pending.position_title,
    }
    create_school_with_owner(user, school_data)

    pending.delete()

    logger.info(f"Registration completed: {user.email} — {school_data['school_name']}")
    return True, 'Account and school created successfully.', user