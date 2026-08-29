from rest_framework.permissions import BasePermission


class IsSchoolMember(BasePermission):
    """User must belong to at least one school."""
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.school_memberships.filter(is_active=True).exists()
        )


class IsSchoolAdmin(BasePermission):
    """User must have school_admin role."""
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.school_memberships.filter(
                role='school_admin', is_active=True
            ).exists()
        )


class IsBranchManager(BasePermission):
    """User must have branch_manager role."""
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.school_memberships.filter(
                role='branch_manager', is_active=True
            ).exists()
        )


class IsTeacher(BasePermission):
    """User must have teacher role."""
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.school_memberships.filter(
                role='teacher', is_active=True
            ).exists()
        )


class IsSchoolAdminOrBranchManager(BasePermission):
    """User must be school_admin or branch_manager."""
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.school_memberships.filter(
                role_ref__slug__in=['proprietor', 'assistant_head'],
                is_active=True
            ).exists()
        )