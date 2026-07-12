from django.utils import timezone


# ── SMS Templates ────────────────────────────────────────────────────────────

def build_enrolment_sms(student, school):
    return (
        f"[{school.name}] Welcome! {student.full_name} has been successfully "
        f"enrolled. Student ID: {student.student_id}. "
        f"Contact us: {getattr(school, 'phone', '')}."
    )


# ── Notification Helpers ─────────────────────────────────────────────────────

def notify_guardian_enrolment(student, school):
    """
    Sends an enrolment confirmation SMS to the primary guardian.
    Never raises — logs and swallows any failure so enrolment always succeeds
    regardless of SMS delivery status.
    """
    import logging
    logger = logging.getLogger(__name__)

    from apps.students.models import StudentGuardian
    from apps.attendance.services.sms_service import send_sms

    primary = StudentGuardian.objects.filter(
        student=student, is_primary=True
    ).select_related('guardian').first()

    if not primary or not primary.guardian.phone:
        logger.info(f"No primary guardian phone found for {student.full_name}; skipping enrolment SMS.")
        return

    message = build_enrolment_sms(student, school)

    try:
        success, response = send_sms(primary.guardian.phone, message)
        if not success:
            logger.warning(f"Enrolment SMS failed for {student.full_name}: {response}")
    except Exception as e:
        logger.error(f"Enrolment SMS error for {student.full_name}: {str(e)}")