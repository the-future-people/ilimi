"""
Records every request an Ilimi support engineer makes while a session is
open, and refuses cross-school requests when one is not.

Deliberately fails closed: if a staff user reaches a school's data without
an open session, the request is denied rather than logged and allowed.
"""
import logging

from django.http import JsonResponse

from apps.agamotto.services.support import any_active_session, record_access

logger = logging.getLogger(__name__)

# Paths that are Ilimi's own rather than a school's, so they need no session.
EXEMPT_PREFIXES = (
    '/admin/',
    '/api/v1/agamotto/',
    '/api/v1/auth/',
    '/api/schema',
    '/api/docs',
    '/static/',
    '/media/',
)


class SupportSessionMiddleware:
    """
    Applies only to users flagged as Ilimi staff. Everyone else — every
    school user — passes through untouched.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)

        if not user or not user.is_authenticated or not user.is_staff:
            return self.get_response(request)

        if request.path.startswith(EXEMPT_PREFIXES):
            return self.get_response(request)

        session = any_active_session(user)

        if session is None:
            logger.warning(
                f'Staff user {user.pk} reached {request.path} with no open '
                f'support session'
            )
            return JsonResponse(
                {
                    'status': 'error',
                    'message': (
                        'Open a support session before accessing a school. '
                        'Access without one is not permitted.'
                    ),
                    'data': None,
                    'errors': None,
                },
                status=403,
            )

        response = self.get_response(request)
        record_access(session, request, getattr(response, 'status_code', None))
        return response