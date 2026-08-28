"""
Password reset by phone.

One flow for everyone — staff, school owners, and parents later. Email
is deliberately not used: a large share of users have no working address,
and the placeholder ones have no inbox at all.
"""
import logging
import secrets

from django.utils import timezone

from apps.accounts.models import User, PasswordResetOTP
from apps.core.phone import normalise_phone, is_valid_phone
from apps.notifications.services.sms import send_sms

logger = logging.getLogger(__name__)


def _generate_code():
    return f'{secrets.randbelow(1000000):06d}'


def request_reset(raw_phone):
    """
    Send a code if the number belongs to an active account.

    Always reports the same thing to the caller. Saying 'no account with
    that number' would let anyone test numbers to find real users.
    """
    if not is_valid_phone(raw_phone):
        return False, 'Enter a valid Ghana phone number, e.g. 0244558389.'

    phone = normalise_phone(raw_phone)
    user = User.objects.filter(phone_number=phone, is_active=True).first()

    if not user:
        logger.info(f'Password reset requested for unknown number {phone}')
        return True, 'If that number is registered, a code has been sent.'

    # One live code at a time, so there is no confusion about which SMS
    # is the current one.
    PasswordResetOTP.objects.filter(user=user, used_at__isnull=True).delete()

    otp = PasswordResetOTP.objects.create(user=user, code=_generate_code())

    result = send_sms(
        phone,
        f'Your Ilimi password reset code is {otp.code}. It expires in 10 minutes.',
    )

    if result.get('status') != 'success':
        logger.error(f'Reset SMS failed for {phone}: {result.get("message")}')

    return True, 'If that number is registered, a code has been sent.'


def verify_code(raw_phone, code):
    """
    Check the code and hand back a ticket.

    The ticket exists so a rejected new password does not burn the code
    and force another SMS.
    """
    generic = 'That code is not right, or it has expired.'

    if not is_valid_phone(raw_phone):
        return False, generic, None

    phone = normalise_phone(raw_phone)
    user = User.objects.filter(phone_number=phone, is_active=True).first()
    if not user:
        return False, generic, None

    otp = PasswordResetOTP.objects.filter(
        user=user, used_at__isnull=True
    ).order_by('-created_at').first()

    if not otp or not otp.is_usable:
        return False, generic, None

    if otp.code != str(code).strip():
        otp.attempts += 1
        otp.save(update_fields=['attempts'])
        if otp.is_exhausted:
            return False, 'Too many wrong attempts. Request a new code.', None
        return False, generic, None

    return True, 'Code accepted.', otp.issue_ticket()


def complete_reset(ticket, new_password):
    """Set the new password and return the user, so the view can sign them in."""
    otp = PasswordResetOTP.objects.select_related('user').filter(
        ticket=ticket, used_at__isnull=True
    ).first()

    if not otp or not otp.ticket_is_valid:
        return False, 'This reset has expired. Start again.', None

    user = otp.user
    user.set_password(new_password)
    user.is_phone_verified = True
    user.save(update_fields=['password', 'is_phone_verified'])

    otp.used_at = timezone.now()
    otp.save(update_fields=['used_at'])

    logger.info(f'Password reset completed for user {user.pk}')
    return True, 'Your password has been changed.', user