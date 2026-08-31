"""
Resolving which school a request is about.

Every school-scoped view needs this, and it used to be copy-pasted into
eleven files. Beyond the duplication, each copy took the requesting user's
first active membership, which is an arbitrary answer for anyone who
belongs to two schools.

Resolution order:
  1. An open support session — Ilimi staff hold no membership at a client
     school, so a session is how they reach it at all.
  2. The membership named by the X-School-Member header, which the app
     sends from whichever school the person selected.
  3. Their only membership, when they have exactly one.
  4. Otherwise an error asking them to choose, rather than a guess.
"""
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.tenants.models import SchoolMember

MEMBER_HEADER = 'HTTP_X_SCHOOL_MEMBER'


class SchoolScopedMixin:
    """Gives a view get_school() and get_member(), resolved once per request."""

    def _resolve(self):
        cached = getattr(self, '_scope', None)
        if cached is not None:
            return cached

        request = self.request
        user = request.user

        # ── Support session ────────────────────────────────────────────────
        if getattr(user, 'is_staff', False):
            from apps.agamotto.services.support import any_active_session
            session = any_active_session(user)
            if session:
                self._scope = (session.school, None)
                return self._scope

        memberships = SchoolMember.objects.filter(
            user=user, is_active=True
        ).select_related('school', 'branch', 'role_ref')

        # ── Named by the app ───────────────────────────────────────────────
        member_id = request.META.get(MEMBER_HEADER)
        if member_id:
            try:
                member = memberships.get(pk=int(member_id))
            except (SchoolMember.DoesNotExist, ValueError, TypeError):
                raise PermissionDenied('That membership is not yours, or is not active.')
            self._scope = (member.school, member)
            return self._scope

        # ── Exactly one, or ask ────────────────────────────────────────────
        found = list(memberships[:2])
        if not found:
            raise NotFound('No school found for your account.')
        if len(found) > 1:
            raise PermissionDenied(
                'You belong to more than one school. Choose which one you are '
                'working in.'
            )

        self._scope = (found[0].school, found[0])
        return self._scope

    def get_school(self):
        return self._resolve()[0]

    def get_member(self):
        """
        The requesting user's membership.

        None during a support session: Ilimi staff are not members of the
        school they are helping, which is the point.
        """
        member = self._resolve()[1]
        if member is None:
            raise PermissionDenied(
                'This action needs a school membership. Support sessions are '
                'read-only.'
            )
        return member

    def get_member_or_none(self):
        """As get_member, but None rather than an error during a session."""
        return self._resolve()[1]