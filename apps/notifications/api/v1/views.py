from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import extend_schema

from apps.core.renderers import IlimiAPIRenderer
from apps.tenants.models import SchoolMember
from apps.tenants.api.permissions import HasDomainPermission
from apps.notifications.models import PaymentReminderRequest
from apps.notifications.services.sms import send_sms
from apps.notifications.services.reminders import (
    request_reminder, approve_reminder, decline_reminder,
)

from .serializers import (
    PaymentReminderRequestSerializer,
    PaymentReminderRequestCreateSerializer,
)


class SchoolScopedMixin:
    def get_school(self):
        member = SchoolMember.objects.filter(
            user=self.request.user, is_active=True
        ).select_related('school').first()
        if not member:
            raise NotFound("No school found for your account.")
        return member.school

    def get_member(self):
        member = SchoolMember.objects.filter(
            user=self.request.user, is_active=True
        ).select_related('school').first()
        if not member:
            raise NotFound("No school found for your account.")
        return member


@extend_schema(tags=["Notifications"])
class PaymentReminderRequestListCreateView(SchoolScopedMixin, GenericAPIView):
    """
    GET: an accountant sees their own requests; an admin sees every
    request for the school, so the approval queue is complete.
    POST: create a request — gated to 'fees' domain access, so only
    someone who can actually work with fees can ask for a reminder.
    """
    permission_classes = [IsAuthenticated, HasDomainPermission]
    required_domain = 'fees'
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = PaymentReminderRequestSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        member = self.get_member()

        qs = PaymentReminderRequest.objects.filter(school=school).select_related(
            'student', 'requested_by__user', 'reviewed_by__user'
        )
        if member.role not in ('school_admin', 'branch_manager'):
            qs = qs.filter(requested_by=member)

        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        serializer = PaymentReminderRequestSerializer(qs, many=True)
        return Response({'requests': serializer.data, 'count': qs.count()})

    def post(self, request, *args, **kwargs):
        school = self.get_school()
        member = self.get_member()

        serializer = PaymentReminderRequestCreateSerializer(
            data=request.data, context={'school': school}
        )
        serializer.is_valid(raise_exception=True)

        reminder = request_reminder(
            school=school,
            student=serializer.validated_data['student'],
            requested_by=member,
            student_fee=serializer.validated_data.get('student_fee'),
            note=serializer.validated_data.get('note', ''),
        )
        return Response(
            {
                'message': 'Reminder request sent to the admin.',
                **PaymentReminderRequestSerializer(reminder).data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Notifications"])
class PaymentReminderApproveView(SchoolScopedMixin, GenericAPIView):
    """
    Admin-only — approving is the actual send action, so it stays behind
    a role check, not just fees-domain access (an accountant must never
    be able to approve her own request).
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = PaymentReminderRequestSerializer

    def get_reminder(self, school, pk):
        try:
            return PaymentReminderRequest.objects.select_related(
                'student'
            ).get(school=school, pk=pk, status='pending')
        except PaymentReminderRequest.DoesNotExist:
            raise NotFound("Pending reminder request not found.")

    def post(self, request, pk, *args, **kwargs):
        school = self.get_school()
        member = self.get_member()

        if member.role not in ('school_admin', 'branch_manager'):
            return Response(
                {'message': 'Only an admin can approve and send reminders.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        reminder = self.get_reminder(school, pk)
        student = reminder.student

        guardian_phone = None
        primary = student.guardians.filter(is_primary=True).select_related('guardian').first()
        if primary:
            guardian_phone = primary.guardian.phone

        if not guardian_phone:
            return Response(
                {'message': 'No guardian phone on file for this student.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        message = request.data.get('message') or (
            f"Dear parent/guardian, this is a reminder regarding "
            f"{student.full_name}'s school fees. Please contact the "
            f"school office at your earliest convenience. Thank you."
        )

        sent = send_sms(guardian_phone, message)
        if not sent:
            return Response(
                {'message': 'SMS could not be sent. The request was not marked as approved — please try again.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        approve_reminder(reminder, reviewed_by=member, message_text=message)
        return Response({
            'message': 'Reminder sent successfully.',
            **PaymentReminderRequestSerializer(reminder).data,
        })


@extend_schema(tags=["Notifications"])
class PaymentReminderDeclineView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = PaymentReminderRequestSerializer

    def post(self, request, pk, *args, **kwargs):
        school = self.get_school()
        member = self.get_member()

        if member.role not in ('school_admin', 'branch_manager'):
            return Response(
                {'message': 'Only an admin can decline a reminder request.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            reminder = PaymentReminderRequest.objects.get(
                school=school, pk=pk, status='pending'
            )
        except PaymentReminderRequest.DoesNotExist:
            raise NotFound("Pending reminder request not found.")

        decline_reminder(
            reminder, reviewed_by=member,
            reason=request.data.get('reason', ''),
        )
        return Response({
            'message': 'Request declined.',
            **PaymentReminderRequestSerializer(reminder).data,
        })