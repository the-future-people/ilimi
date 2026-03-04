import logging
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from apps.accounts.models import User, StaffPortalInvite
from apps.teachers.models import StaffProfile
from apps.notifications.services.sms import send_sms

logger = logging.getLogger(__name__)


def _build_invite_url(request, token):
    """Build the full invite URL."""
    scheme = 'https' if request.is_secure() else 'http'
    host = request.get_host()
    return f"{scheme}://{host}/accounts/staff/setup/{token}/"


@transaction.atomic
def send_staff_portal_invite(staff: StaffProfile, invited_by: User, request) -> tuple:
    """
    Send a portal access invite to a staff member.
    - Creates a User account if one doesn't exist
    - Creates or refreshes a StaffPortalInvite
    - Sends SMS with the setup link
    Returns (success: bool, message: str)
    """

    # ── Check staff has a phone number ────────────────────────────────────────
    if not staff.phone:
        return False, "This staff member has no phone number on record."

    # ── Check if already has active portal access ──────────────────────────────
    if staff.user and staff.user.is_active and staff.user.is_phone_verified:
        return False, f"{staff.full_name} already has active portal access."

    # ── Create User account if not exists ─────────────────────────────────────
    if not staff.user:
        # Use phone as username base, generate unusable password
        email = staff.email if staff.email else f"{staff.staff_id.lower().replace('/', '.')}@noemail.ilimi.app"

        if User.objects.filter(email=email).exists():
            email = f"{staff.staff_id.lower().replace('/', '.')}_{timezone.now().timestamp():.0f}@noemail.ilimi.app"

        user = User.objects.create_user(
            email=email,
            password=None,  # unusable password until they set it
            first_name=staff.first_name,
            last_name=staff.last_name,
            phone_number=staff.phone,
            is_active=True,
        )
        user.set_unusable_password()
        user.save()

        staff.user = user
        staff.save(update_fields=['user'])
        logger.info(f"Created portal user for staff: {staff.full_name} ({staff.staff_id})")
    else:
        user = staff.user

    # ── Create or refresh invite ───────────────────────────────────────────────
    StaffPortalInvite.objects.filter(staff=staff).delete()
    invite = StaffPortalInvite.objects.create(
        staff=staff,
        invited_by=invited_by,
    )

    # ── Build SMS message ──────────────────────────────────────────────────────
    invite_url = _build_invite_url(request, invite.token)
    school_name = staff.school.name
    message = (
        f"Hello {staff.first_name}, you have been granted access to the "
        f"{school_name} staff portal on Ilimi. "
        f"Set up your account here: {invite_url} "
        f"This link expires in 48 hours."
    )

    # ── Send SMS ───────────────────────────────────────────────────────────────
    try:
        send_sms(staff.phone, message)
        logger.info(f"Portal invite SMS sent to {staff.phone} for {staff.full_name}")
    except Exception as e:
        logger.error(f"SMS failed for staff invite {staff.staff_id}: {str(e)}")
        # Don't fail the whole operation — invite still created
        return True, f"Invite created but SMS delivery failed. Share this link manually: {invite_url}"

    return True, f"Portal access invite sent to {staff.first_name} via SMS ({staff.phone})."


from apps.tenants.models import SchoolMember

def accept_staff_invite(token: str, password: str) -> tuple:
    """
    Accept a staff portal invite and set password.
    Creates a SchoolMember record so the teacher can access their portal.
    Returns (success: bool, message: str, user: User|None)
    """
    try:
        invite = StaffPortalInvite.objects.select_related(
            'staff', 'staff__user', 'staff__school'
        ).get(token=token)
    except StaffPortalInvite.DoesNotExist:
        return False, "This invite link is invalid or has already been used.", None

    if not invite.is_valid:
        if invite.is_expired:
            return False, "This invite link has expired. Please ask your administrator to resend it.", None
        return False, "This invite link has already been used.", None

    user = invite.staff.user
    if not user:
        return False, "No user account found for this invite.", None

    # ── Set password ───────────────────────────────────────────────────────────
    user.set_password(password)
    user.is_phone_verified = True
    user.save(update_fields=['password', 'is_phone_verified'])

    # ── Create SchoolMember if not exists ──────────────────────────────────────
    SchoolMember.objects.get_or_create(
        user=user,
        school=invite.staff.school,
        defaults={
            'role': 'teacher',
            'branch': invite.staff.branch,
            'is_active': True,
        }
    )

    # ── Mark invite accepted ───────────────────────────────────────────────────
    invite.status = 'accepted'
    invite.save(update_fields=['status'])

    logger.info(f"Staff portal invite accepted: {invite.staff.full_name}")
    return True, "Account set up successfully. You can now log in.", user