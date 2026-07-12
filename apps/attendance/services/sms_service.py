from django.utils import timezone


# ── SMS Templates ──────────────────────────────────────────────────────────────

def build_checkin_sms(student, clock_in_time, status, school):
    time_str = clock_in_time.strftime('%I:%M %p') if clock_in_time else 'N/A'
    if status == 'late':
        return (
            f"[{school.name}] {student.full_name} has arrived LATE at "
            f"{time_str}. Please ensure punctuality. "
            f"Contact us: {getattr(school, 'phone', '')}."
        )
    return (
        f"[{school.name}] {student.full_name} has arrived safely at "
        f"{time_str}. Have a great day!"
    )


def build_checkout_sms(student, clock_out_time, picked_up_by, school):
    time_str = clock_out_time.strftime('%I:%M %p') if clock_out_time else 'N/A'
    collector = picked_up_by.full_name if picked_up_by else 'an authorised person'
    return (
        f"[{school.name}] {student.full_name} has been collected by "
        f"{collector} at {time_str}. "
        f"Contact us: {getattr(school, 'phone', '')}."
    )


def build_absence_sms(student, school):
    return (
        f"[{school.name}] This is to inform you that {student.full_name} "
        f"has NOT reported to school today. Please contact us if this is unexpected: "
        f"{getattr(school, 'phone', '')}."
    )


def build_unclocked_out_sms(student, school):
    return (
        f"[{school.name}] ALERT: {student.full_name} has not been collected "
        f"from school yet. Please arrange pickup immediately or contact us: "
        f"{getattr(school, 'phone', '')}."
    )


def build_pickup_authorisation_sms(student, attempted_by_name, school):
    return (
        f"[{school.name}] ALERT: {attempted_by_name} is attempting to collect "
        f"{student.full_name} from school. If you authorise this, please call "
        f"us immediately: {getattr(school, 'phone', '')}. "
        f"If you did NOT send this person, contact us urgently."
    )


# ── Sender ─────────────────────────────────────────────────────────────────────

def send_sms(phone_number, message):
    """
    Sends an SMS using the canonical, pluggable SMS backend
    (Console in dev, Arkesel in production — controlled by settings.SMS_BACKEND).
    Returns (success: bool, response: dict) to preserve this file's existing call signature.
    """
    from apps.notifications.services.sms import send_sms as canonical_send_sms

    result = canonical_send_sms(phone_number, message)
    success = result.get('status') == 'success'
    return success, result


# ── Notification Helpers ───────────────────────────────────────────────────────

def notify_guardian_checkin(student, attendance_record):
    """
    Send check-in SMS to all guardians.
    Updates guardian_notified and notification_sent_at on success.
    """
    from apps.students.models import StudentGuardian
    from apps.attendance.services.attendance_service import get_attendance_settings

    settings = get_attendance_settings(
        attendance_record.school, attendance_record.branch
    )
    if not settings or not settings.sms_on_checkin:
        return

    guardians = StudentGuardian.objects.filter(
        student=student
    ).select_related('guardian')

    message = build_checkin_sms(
        student,
        attendance_record.clock_in_time,
        attendance_record.status,
        attendance_record.school,
    )

    any_sent = False
    for sg in guardians:
        if sg.guardian.phone:
            success, _ = send_sms(sg.guardian.phone, message)
            if success:
                any_sent = True

    if any_sent:
        attendance_record.guardian_notified = True
        attendance_record.notification_sent_at = timezone.now()
        attendance_record.save(
            update_fields=['guardian_notified', 'notification_sent_at']
        )


def notify_guardian_checkout(student, attendance_record):
    """Send checkout SMS to all guardians."""
    from apps.students.models import StudentGuardian
    from apps.attendance.services.attendance_service import get_attendance_settings

    settings = get_attendance_settings(
        attendance_record.school, attendance_record.branch
    )
    if not settings or not settings.sms_on_checkout:
        return

    guardians = StudentGuardian.objects.filter(
        student=student
    ).select_related('guardian')

    message = build_checkout_sms(
        student,
        attendance_record.clock_out_time,
        attendance_record.picked_up_by,
        attendance_record.school,
    )

    for sg in guardians:
        if sg.guardian.phone:
            send_sms(sg.guardian.phone, message)


def notify_guardian_absence(student, school):
    """Send absence SMS to primary guardian."""
    from apps.students.models import StudentGuardian

    primary = StudentGuardian.objects.filter(
        student=student, is_primary=True
    ).select_related('guardian').first()

    if not primary or not primary.guardian.phone:
        return

    message = build_absence_sms(student, school)
    send_sms(primary.guardian.phone, message)


def notify_pickup_authorisation(incident):
    """
    SMS the primary guardian when an unrecognised person attempts pickup.
    Updates the incident record with SMS sent status.
    """
    from apps.students.models import StudentGuardian

    primary = StudentGuardian.objects.filter(
        student=incident.student, is_primary=True
    ).select_related('guardian').first()

    if not primary or not primary.guardian.phone:
        return

    message = build_pickup_authorisation_sms(
        incident.student,
        incident.attempted_by_name,
        incident.school,
    )

    success, _ = send_sms(primary.guardian.phone, message)

    if success:
        incident.authorisation_sms_sent = True
        incident.authorisation_sms_sent_at = timezone.now()
        incident.guardian_notified = primary.guardian
        incident.save(update_fields=[
            'authorisation_sms_sent',
            'authorisation_sms_sent_at',
            'guardian_notified',
        ])