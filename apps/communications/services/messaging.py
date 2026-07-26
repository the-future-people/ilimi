"""
Ties Message, the audience resolver, and send_sms together. Two entry
points: send_message (fires immediately — used when an admin composes,
or when a pending message gets approved) and request_message (creates a
pending_approval record for a non-admin composer, sends nothing yet).
"""

from django.utils import timezone

from apps.communications.models import Message
from apps.communications.services.audience import resolve_recipients


def request_message(school, composed_by, title, body, audience_type, **targets):
    """Create a message awaiting admin approval. Nothing is sent yet."""
    return Message.objects.create(
        school=school,
        composed_by=composed_by,
        title=title,
        body=body,
        audience_type=audience_type,
        status='pending_approval',
        **targets,
    )


def send_message(message, sent_by=None):
    """
    Resolves the audience and actually sends. Used both when an admin
    composes directly (sent_by is the composer, no separate reviewer) and
    when approving a pending message (sent_by is the approver).

    Returns (success_count, failure_count). Never raises on individual SMS
    failures — one bad number shouldn't block the rest of the send.
    """
    from apps.notifications.services.sms import send_sms

    recipients = resolve_recipients(message)
    success_count = 0
    failure_count = 0

    for recipient in recipients:
        try:
            sent = send_sms(recipient['phone'], message.body)
            if sent:
                success_count += 1
            else:
                failure_count += 1
        except Exception:
            failure_count += 1

    message.status = 'sent' if success_count > 0 else 'failed'
    message.recipient_count = success_count
    message.sent_at = timezone.now()
    if sent_by and sent_by != message.composed_by:
        message.reviewed_by = sent_by
        message.reviewed_at = timezone.now()
    message.save()

    return success_count, failure_count


def approve_message(message, reviewed_by):
    """Approve a pending message and send it in the same action."""
    message.status = 'approved'
    message.reviewed_by = reviewed_by
    message.reviewed_at = timezone.now()
    message.save()
    return send_message(message, sent_by=reviewed_by)


def decline_message(message, reviewed_by, reason=''):
    message.status = 'declined'
    message.reviewed_by = reviewed_by
    message.reviewed_at = timezone.now()
    message.decline_reason = reason
    message.save()
    return message