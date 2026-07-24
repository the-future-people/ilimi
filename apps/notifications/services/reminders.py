"""
Payment reminder request workflow: an accountant flags a nudge is needed,
an admin approves (sending the real SMS via send_sms) or declines.
"""

from django.utils import timezone

from apps.notifications.models import PaymentReminderRequest


def request_reminder(school, student, requested_by, student_fee=None, note=''):
    return PaymentReminderRequest.objects.create(
        school=school,
        student=student,
        student_fee=student_fee,
        requested_by=requested_by,
        note=note,
    )


def approve_reminder(reminder, reviewed_by, message_text):
    """
    Marks the request approved and records what was sent. The actual SMS
    send happens in the view BEFORE this is called — this only logs it,
    so a send failure never leaves a request wrongly marked approved.
    """
    reminder.status = 'approved'
    reminder.reviewed_by = reviewed_by
    reminder.reviewed_at = timezone.now()
    reminder.message_sent = message_text
    reminder.sent_at = timezone.now()
    reminder.save()
    return reminder


def decline_reminder(reminder, reviewed_by, reason=''):
    reminder.status = 'declined'
    reminder.reviewed_by = reviewed_by
    reminder.reviewed_at = timezone.now()
    reminder.decline_reason = reason
    reminder.save()
    return reminder