from rest_framework.permissions import BasePermission

from apps.tenants.models import SchoolMember
from apps.tenants.permissions import has_domain_access


class HasDomainPermission(BasePermission):
    """
    Gate a view by the requesting user's SchoolMember role against the
    ROLE_PERMISSIONS map. Set `required_domain` (and optionally
    `required_level`, default 'full') as class attributes on the view.

    Deliberately does its own SchoolMember lookup rather than assuming
    SchoolScopedMixin already ran — this permission class can be attached
    to any view, mixin or not.
    """

    def has_permission(self, request, view):
        domain = getattr(view, 'required_domain', None)
        if domain is None:
            # Fail closed: a view that forgets to declare its domain does
            # not silently get through.
            return False

        level = getattr(view, 'required_level', 'full')

        member = SchoolMember.objects.filter(
            user=request.user, is_active=True
        ).first()

        return has_domain_access(member, domain, level)