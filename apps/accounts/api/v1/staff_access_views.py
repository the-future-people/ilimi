from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import extend_schema

from apps.core.renderers import IlimiAPIRenderer
from apps.tenants.models import SchoolMember
from apps.teachers.models import StaffProfile
from apps.accounts.models import StaffPortalInvite
from apps.accounts.services.staff_invite import (
    send_staff_portal_invite,
    accept_staff_invite,
)


@extend_schema(tags=["Staff Access"])
class StaffInviteView(GenericAPIView):
    """Admin grants portal access to a staff member."""

    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, staff_pk, *args, **kwargs):
        member = SchoolMember.objects.filter(
            user=request.user, is_active=True
        ).select_related('school').first()

        if not member or member.role not in ('school_admin', 'branch_manager'):
            return Response({'message': 'Only an administrator can grant portal access.'}, status=403)

        try:
            staff = StaffProfile.objects.select_related('school', 'user').get(
                pk=staff_pk, school=member.school
            )
        except StaffProfile.DoesNotExist:
            raise NotFound("Staff member not found.")

        role = request.data.get('role', 'teacher')
        valid_roles = {r[0] for r in SchoolMember.ROLE_CHOICES}
        if role not in valid_roles:
            return Response({'message': f"'{role}' is not a valid role."}, status=400)

        success, message, invite_url = send_staff_portal_invite(
            staff=staff, invited_by=request.user, request=request, role=role,
        )

        if not success:
            return Response({'message': message}, status=400)

        invite = StaffPortalInvite.objects.filter(staff=staff).first()

        return Response({
            'message': message,
            'invite_url': invite_url,
            'expires_at': invite.expires_at if invite else None,
            'role': role,
        })


@extend_schema(tags=["Staff Access"])
class StaffInviteAcceptView(GenericAPIView):
    """Public. The staff member opens their link and sets a password."""

    permission_classes = [AllowAny]
    renderer_classes = [IlimiAPIRenderer]
    authentication_classes = []

    def get(self, request, token, *args, **kwargs):
        try:
            invite = StaffPortalInvite.objects.select_related(
                'staff', 'staff__school'
            ).get(token=token)
        except (StaffPortalInvite.DoesNotExist, ValueError):
            raise NotFound("This link is not valid.")

        if not invite.is_valid:
            return Response({
                'valid': False,
                'message': (
                    'This link has expired. Ask your administrator to send a new one.'
                    if invite.is_expired
                    else 'This link has already been used.'
                ),
            }, status=400)

        return Response({
            'valid': True,
            'full_name': invite.staff.full_name,
            'school_name': invite.staff.school.name,
            'role': invite.role,
            'expires_at': invite.expires_at,
        })

    def post(self, request, token, *args, **kwargs):
        password = request.data.get('password', '')
        confirm = request.data.get('confirm_password', '')

        if len(password) < 8:
            return Response({'message': 'Your password needs at least 8 characters.'}, status=400)
        if password != confirm:
            return Response({'message': 'The two passwords do not match.'}, status=400)

        success, message, user = accept_staff_invite(str(token), password)

        if not success:
            return Response({'message': message}, status=400)

        return Response({'message': message, 'email': user.email})