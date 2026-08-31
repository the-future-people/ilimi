"""
Support sessions.

Ilimi holds no standing access to a school's records. A support engineer
opens a session against one school, stating why; it expires on its own;
every request made while it is open is recorded; and the school receives a
readable summary when it closes.
"""
import logging

from django.utils import timezone

from apps.agamotto.models import SupportSession, SupportAccessLog

logger = logging.getLogger(__name__)


def open_session(user, school, reason):
    """
    Start a session, or return the one already running.

    One live session per engineer per school: reopening while one is open
    would fragment the record for no benefit.
    """
    reason = (reason or '').strip()
    if not reason:
        return None, 'State why you need access to this school.'

    existing = active_session(user, school)
    if existing:
        return existing, 'You already have an open session on this school.'

    session = SupportSession.objects.create(
        school=school,
        opened_by=user,
        reason=reason,
    )
    logger.info(
        f'Support session {session.pk} opened on school {school.pk} '
        f'by user {user.pk}'
    )
    return session, 'Session opened.'


def active_session(user, school):
    """The engineer's open, unexpired session on this school, if any."""
    return SupportSession.objects.filter(
        opened_by=user,
        school=school,
        closed_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).first()


def any_active_session(user):
    """
    Any school this engineer currently has open.

    Used per request, so it stays a single indexed query.
    """
    return SupportSession.objects.filter(
        opened_by=user,
        closed_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).select_related('school').first()


def record_access(session, request, status_code=None):
    """Write one request to the session's log."""
    try:
        SupportAccessLog.objects.create(
            session=session,
            method=request.method[:10],
            path=request.path[:255],
            query=request.META.get('QUERY_STRING', '')[:255],
            status_code=status_code,
        )
    except Exception as e:
        # Never let logging break the request being logged. A failure here
        # is serious, so it is shouted about rather than swallowed quietly.
        logger.error(f'Failed to record support access: {e}')


def close_session(session, send_summary=True):
    """Close a session and send the school its summary."""
    session.close()
    logger.info(f'Support session {session.pk} closed')

    if send_summary:
        from apps.agamotto.services.support_summary import send_session_summary
        send_session_summary(session)

    return session


def close_expired_sessions():
    """
    Close sessions that have run past their window.

    Called on a schedule. Sessions expire on their own so that closing one
    is never left to somebody remembering.
    """
    expired = SupportSession.objects.filter(
        closed_at__isnull=True,
        expires_at__lte=timezone.now(),
    )
    count = 0
    for session in expired:
        close_session(session)
        count += 1
    return count