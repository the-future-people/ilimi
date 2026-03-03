from datetime import date as dt_date

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from drf_spectacular.utils import extend_schema

from apps.core.renderers import IlimiAPIRenderer
from apps.tenants.models import SchoolMember
from apps.academics.models import Term
from apps.attendance.models import (
    StudentAttendance,
    StaffAttendance,
    AttendanceSettings,
    AuthorisedPickup,
    PickupIncident,
)
from apps.attendance.services.attendance_service import (
    get_attendance_settings,
    get_active_term,
    mark_student_attendance,
    bulk_mark_student_attendance,
    checkout_student,
    override_locked_record,
    mark_staff_attendance,
    bulk_mark_staff_attendance,
    get_student_attendance_summary,
    get_staff_attendance_summary,
)
from apps.attendance.services.sms_service import (
    notify_guardian_checkin,
    notify_guardian_checkout,
    notify_pickup_authorisation,
)
from .serializers import (
    AttendanceSettingsSerializer,
    AuthorisedPickupSerializer,
    AuthorisedPickupCreateSerializer,
    PickupIncidentSerializer,
    PickupIncidentCreateSerializer,
    PickupIncidentResolveSerializer,
    StudentAttendanceSerializer,
    StudentAttendanceListSerializer,
    StudentAttendanceCreateSerializer,
    StudentAttendanceBulkSerializer,
    StudentCheckoutSerializer,
    StudentAttendanceUpdateSerializer,
    StaffAttendanceSerializer,
    StaffAttendanceListSerializer,
    StaffAttendanceCreateSerializer,
    StaffAttendanceBulkSerializer,
    StaffAttendanceUpdateSerializer,
    DeviceIngestSerializer,
)


# ── Mixin ──────────────────────────────────────────────────────────────────────

class SchoolScopedMixin:
    def get_school(self):
        member = SchoolMember.objects.filter(
            user=self.request.user, is_active=True
        ).select_related('school').first()
        if not member:
            raise NotFound("No active school found for your account.")
        return member.school

    def get_member(self):
        member = SchoolMember.objects.filter(
            user=self.request.user, is_active=True
        ).select_related('school', 'branch').first()
        if not member:
            raise NotFound("No active school found for your account.")
        return member


# ── Attendance Settings ────────────────────────────────────────────────────────

@extend_schema(tags=["Attendance Settings"])
class AttendanceSettingsView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = AttendanceSettingsSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        branch_id = request.query_params.get('branch')
        settings = get_attendance_settings(school, branch_id)

        if not settings:
            return Response(
                {'message': 'No attendance settings configured yet.', 'data': None}
            )

        serializer = AttendanceSettingsSerializer(settings)
        return Response({
            'message': 'Attendance settings retrieved.',
            'data': serializer.data,
        })

    def put(self, request, *args, **kwargs):
        school = self.get_school()
        branch_id = request.data.get('branch')
        settings = get_attendance_settings(school, branch_id)

        if settings:
            serializer = AttendanceSettingsSerializer(
                settings, data=request.data, partial=True
            )
        else:
            serializer = AttendanceSettingsSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        instance = serializer.save(school=school)

        return Response({
            'message': 'Attendance settings saved.',
            'data': AttendanceSettingsSerializer(instance).data,
        })


# ── Authorised Pickup ──────────────────────────────────────────────────────────

@extend_schema(tags=["Authorised Pickups"])
class AuthorisedPickupListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        qs = AuthorisedPickup.objects.filter(
            school=school
        ).select_related('student', 'added_by')

        student_id = request.query_params.get('student')
        is_active = request.query_params.get('is_active')
        search = request.query_params.get('search')

        if student_id:
            qs = qs.filter(student_id=student_id)
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        if search:
            qs = qs.filter(first_name__icontains=search) | \
                 qs.filter(last_name__icontains=search) | \
                 qs.filter(phone__icontains=search)

        serializer = AuthorisedPickupSerializer(qs, many=True)
        return Response({
            'message': 'Authorised pickup persons retrieved.',
            'data': serializer.data,
            'count': qs.count(),
        })

    def post(self, request, *args, **kwargs):
        member = self.get_member()
        school = member.school

        serializer = AuthorisedPickupCreateSerializer(
            data=request.data, context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        pickup = serializer.save(school=school, added_by=member)

        return Response({
            'message': f"{pickup.full_name} added as an authorised pickup person.",
            'data': AuthorisedPickupSerializer(pickup).data,
        }, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Authorised Pickups"])
class AuthorisedPickupDetailView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def get_object(self, school, pk):
        try:
            return AuthorisedPickup.objects.get(school=school, pk=pk)
        except AuthorisedPickup.DoesNotExist:
            raise NotFound("Authorised pickup person not found.")

    def get(self, request, pk, *args, **kwargs):
        school = self.get_school()
        pickup = self.get_object(school, pk)
        return Response({
            'message': 'Authorised pickup person retrieved.',
            'data': AuthorisedPickupSerializer(pickup).data,
        })

    def patch(self, request, pk, *args, **kwargs):
        school = self.get_school()
        pickup = self.get_object(school, pk)
        serializer = AuthorisedPickupCreateSerializer(
            pickup, data=request.data, partial=True,
            context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': f"{pickup.full_name} updated successfully.",
            'data': AuthorisedPickupSerializer(pickup).data,
        })

    def delete(self, request, pk, *args, **kwargs):
        school = self.get_school()
        pickup = self.get_object(school, pk)
        name = pickup.full_name
        pickup.delete()
        return Response({
            'message': f"{name} removed from authorised pickup persons.",
        })


# ── Pickup Incidents ───────────────────────────────────────────────────────────

@extend_schema(tags=["Pickup Incidents"])
class PickupIncidentListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        qs = PickupIncident.objects.filter(
            school=school
        ).select_related('student', 'guardian_notified', 'resolved_by')

        student_id = request.query_params.get('student')
        status_filter = request.query_params.get('status')
        escalated = request.query_params.get('escalated')

        if student_id:
            qs = qs.filter(student_id=student_id)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if escalated is not None:
            qs = qs.filter(escalated=escalated.lower() == 'true')

        serializer = PickupIncidentSerializer(qs, many=True)
        return Response({
            'message': 'Pickup incidents retrieved.',
            'data': serializer.data,
            'count': qs.count(),
        })

    def post(self, request, *args, **kwargs):
        """Log a new unauthorised pickup attempt."""
        member = self.get_member()
        school = member.school

        serializer = PickupIncidentCreateSerializer(
            data=request.data, context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        incident = serializer.save(school=school)

        # Immediately notify guardian via SMS
        notify_pickup_authorisation(incident)

        return Response({
            'message': (
                f"Pickup incident logged for {incident.student.full_name}. "
                f"Guardian has been notified via SMS."
            ),
            'data': PickupIncidentSerializer(incident).data,
        }, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Pickup Incidents"])
class PickupIncidentDetailView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def get_object(self, school, pk):
        try:
            return PickupIncident.objects.select_related(
                'student', 'guardian_notified', 'resolved_by'
            ).get(school=school, pk=pk)
        except PickupIncident.DoesNotExist:
            raise NotFound("Pickup incident not found.")

    def get(self, request, pk, *args, **kwargs):
        school = self.get_school()
        incident = self.get_object(school, pk)
        return Response({
            'message': 'Pickup incident retrieved.',
            'data': PickupIncidentSerializer(incident).data,
        })

    def patch(self, request, pk, *args, **kwargs):
        """Resolve a pickup incident."""
        member = self.get_member()
        school = member.school
        incident = self.get_object(school, pk)

        if incident.is_resolved:
            raise PermissionDenied("This incident has already been resolved.")

        serializer = PickupIncidentResolveSerializer(
            incident, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        from django.utils import timezone
        incident = serializer.save(
            resolved_by=member,
            resolved_at=timezone.now(),
            status=request.data.get('status', incident.status),
        )

        return Response({
            'message': f"Pickup incident resolved — {incident.get_status_display()}.",
            'data': PickupIncidentSerializer(incident).data,
        })


# ── Student Attendance ─────────────────────────────────────────────────────────

@extend_schema(tags=["Student Attendance"])
class StudentAttendanceListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        qs = StudentAttendance.objects.filter(
            school=school
        ).select_related('student', 'term', 'branch', 'marked_by', 'picked_up_by')

        # Filters
        student_id = request.query_params.get('student')
        term_id = request.query_params.get('term')
        date = request.query_params.get('date')
        status_filter = request.query_params.get('status')
        branch_id = request.query_params.get('branch')
        search = request.query_params.get('search')

        if student_id:
            qs = qs.filter(student_id=student_id)
        if term_id:
            qs = qs.filter(term_id=term_id)
        if date:
            qs = qs.filter(date=date)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if search:
            qs = (
                qs.filter(student__first_name__icontains=search) |
                qs.filter(student__last_name__icontains=search) |
                qs.filter(student__student_id__icontains=search)
            )

        serializer = StudentAttendanceListSerializer(qs, many=True)
        return Response({
            'message': 'Student attendance records retrieved.',
            'data': serializer.data,
            'count': qs.count(),
        })

    def post(self, request, *args, **kwargs):
        member = self.get_member()
        school = member.school

        serializer = StudentAttendanceCreateSerializer(
            data=request.data, context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        record, created = mark_student_attendance(
            school=school,
            student=data['student'],
            term=data['term'],
            status=data['status'],
            date=data.get('date'),
            clock_in_time=data.get('clock_in_time'),
            source='manual',
            marked_by=member,
            branch=data.get('branch', member.branch),
            remarks=data.get('remarks', ''),
        )

        # Send guardian SMS synchronously for now
        # TODO: replace with task_notify_guardian_checkin.delay(record.pk)
        if created:
            notify_guardian_checkin(record.student, record)

        action = 'created' if created else 'updated'
        return Response({
            'message': f"Attendance record {action} for {record.student.full_name}.",
            'data': StudentAttendanceSerializer(record).data,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@extend_schema(tags=["Student Attendance"])
class StudentAttendanceBulkView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, *args, **kwargs):
        member = self.get_member()
        school = member.school

        serializer = StudentAttendanceBulkSerializer(
            data=request.data, context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        term = Term.objects.get(pk=data['term_id'], school=school)

        results = bulk_mark_student_attendance(
            school=school,
            term=term,
            records=data['records'],
            marked_by=member,
            branch=member.branch,
            date=data.get('date'),
        )

        total_processed = len(results['created']) + len(results['updated'])
        return Response({
            'message': f"{total_processed} attendance records processed.",
            'data': results,
        }, status=status.HTTP_207_MULTI_STATUS if results['errors'] else status.HTTP_200_OK)


@extend_schema(tags=["Student Attendance"])
class StudentAttendanceDetailView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def get_object(self, school, pk):
        try:
            return StudentAttendance.objects.select_related(
                'student', 'term', 'branch', 'marked_by',
                'picked_up_by', 'pickup_verified_by', 'override_by'
            ).get(school=school, pk=pk)
        except StudentAttendance.DoesNotExist:
            raise NotFound("Student attendance record not found.")

    def get(self, request, pk, *args, **kwargs):
        school = self.get_school()
        record = self.get_object(school, pk)
        return Response({
            'message': 'Student attendance record retrieved.',
            'data': StudentAttendanceSerializer(record).data,
        })

    def patch(self, request, pk, *args, **kwargs):
        member = self.get_member()
        school = member.school
        record = self.get_object(school, pk)

        serializer = StudentAttendanceUpdateSerializer(
            record, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        if record.locked:
            override_reason = serializer.validated_data.get('override_reason', '')
            fields = {
                k: v for k, v in serializer.validated_data.items()
                if k != 'override_reason'
            }
            record = override_locked_record(
                record, override_reason, member, **fields
            )
        else:
            serializer.save()

        return Response({
            'message': f"Attendance record updated for {record.student.full_name}.",
            'data': StudentAttendanceSerializer(record).data,
        })

    def delete(self, request, pk, *args, **kwargs):
        school = self.get_school()
        record = self.get_object(school, pk)

        if record.locked and not request.user.is_superuser:
            raise PermissionDenied(
                "Locked fingerprint records can only be deleted by a superuser."
            )

        name = record.student.full_name
        record.delete()
        return Response({'message': f"Attendance record for {name} deleted."})


@extend_schema(tags=["Student Attendance"])
class StudentCheckoutView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, pk, *args, **kwargs):
        member = self.get_member()
        school = member.school

        try:
            record = StudentAttendance.objects.get(school=school, pk=pk)
        except StudentAttendance.DoesNotExist:
            raise NotFound("Student attendance record not found.")

        if record.is_clocked_out:
            return Response({
                'message': f"{record.student.full_name} has already been clocked out.",
                'data': StudentAttendanceSerializer(record).data,
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = StudentCheckoutSerializer(
            data=request.data, context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        picked_up_by = None
        if data.get('picked_up_by_id'):
            picked_up_by = AuthorisedPickup.objects.get(
                pk=data['picked_up_by_id'], school=school
            )

        pickup_verified_by = None
        if data.get('pickup_verified_by_id'):
            try:
                pickup_verified_by = SchoolMember.objects.get(
                    pk=data['pickup_verified_by_id'], school=school
                )
            except SchoolMember.DoesNotExist:
                pass

        record = checkout_student(
            attendance_record=record,
            clock_out_time=data.get('clock_out_time'),
            picked_up_by=picked_up_by,
            pickup_verified_by=pickup_verified_by,
            early_dismissal_reason=data.get('early_dismissal_reason', ''),
        )

        # Notify guardian of checkout
        # TODO: replace with task_notify_guardian_checkout.delay(record.pk)
        notify_guardian_checkout(record.student, record)

        return Response({
            'message': f"{record.student.full_name} successfully clocked out.",
            'data': StudentAttendanceSerializer(record).data,
        })


@extend_schema(tags=["Student Attendance"])
class StudentAttendanceSummaryView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def get(self, request, *args, **kwargs):
        school = self.get_school()

        student_id = request.query_params.get('student')
        term_id = request.query_params.get('term')

        if not student_id or not term_id:
            return Response({
                'message': 'Both student and term query parameters are required.',
            }, status=status.HTTP_400_BAD_REQUEST)

        from apps.students.models import Student
        try:
            student = Student.objects.get(pk=student_id, school=school)
            term = Term.objects.get(pk=term_id, school=school)
        except (Student.DoesNotExist, Term.DoesNotExist):
            raise NotFound("Student or term not found.")

        summary = get_student_attendance_summary(student, term)

        return Response({
            'message': f"Attendance summary for {student.full_name}.",
            'data': {
                'student': student_id,
                'student_name': student.full_name,
                'term': term_id,
                'term_name': str(term),
                **summary,
            },
        })


# ── Staff Attendance ───────────────────────────────────────────────────────────

@extend_schema(tags=["Staff Attendance"])
class StaffAttendanceListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        qs = StaffAttendance.objects.filter(
            school=school
        ).select_related('staff', 'term', 'branch')

        staff_id = request.query_params.get('staff')
        term_id = request.query_params.get('term')
        date = request.query_params.get('date')
        status_filter = request.query_params.get('status')
        branch_id = request.query_params.get('branch')
        search = request.query_params.get('search')

        if staff_id:
            qs = qs.filter(staff_id=staff_id)
        if term_id:
            qs = qs.filter(term_id=term_id)
        if date:
            qs = qs.filter(date=date)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if search:
            qs = (
                qs.filter(staff__first_name__icontains=search) |
                qs.filter(staff__last_name__icontains=search) |
                qs.filter(staff__staff_id__icontains=search)
            )

        serializer = StaffAttendanceListSerializer(qs, many=True)
        return Response({
            'message': 'Staff attendance records retrieved.',
            'data': serializer.data,
            'count': qs.count(),
        })

    def post(self, request, *args, **kwargs):
        member = self.get_member()
        school = member.school

        serializer = StaffAttendanceCreateSerializer(
            data=request.data, context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        record, created = mark_staff_attendance(
            school=school,
            staff=data['staff'],
            term=data['term'],
            status=data['status'],
            date=data.get('date'),
            clock_in_time=data.get('clock_in_time'),
            source='manual',
            branch=data.get('branch', member.branch),
            remarks=data.get('remarks', ''),
        )

        action = 'created' if created else 'updated'
        return Response({
            'message': f"Staff attendance record {action} for {record.staff.full_name}.",
            'data': StaffAttendanceSerializer(record).data,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@extend_schema(tags=["Staff Attendance"])
class StaffAttendanceBulkView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, *args, **kwargs):
        member = self.get_member()
        school = member.school

        serializer = StaffAttendanceBulkSerializer(
            data=request.data, context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        term = Term.objects.get(pk=data['term_id'], school=school)

        results = bulk_mark_staff_attendance(
            school=school,
            term=term,
            records=data['records'],
            branch=member.branch,
            date=data.get('date'),
        )

        total_processed = len(results['created']) + len(results['updated'])
        return Response({
            'message': f"{total_processed} staff attendance records processed.",
            'data': results,
        }, status=status.HTTP_207_MULTI_STATUS if results['errors'] else status.HTTP_200_OK)


@extend_schema(tags=["Staff Attendance"])
class StaffAttendanceDetailView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def get_object(self, school, pk):
        try:
            return StaffAttendance.objects.select_related(
                'staff', 'term', 'branch'
            ).get(school=school, pk=pk)
        except StaffAttendance.DoesNotExist:
            raise NotFound("Staff attendance record not found.")

    def get(self, request, pk, *args, **kwargs):
        school = self.get_school()
        record = self.get_object(school, pk)
        return Response({
            'message': 'Staff attendance record retrieved.',
            'data': StaffAttendanceSerializer(record).data,
        })

    def patch(self, request, pk, *args, **kwargs):
        member = self.get_member()
        school = member.school
        record = self.get_object(school, pk)

        serializer = StaffAttendanceUpdateSerializer(
            record, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        if record.locked:
            override_reason = serializer.validated_data.get('override_reason', '')
            fields = {
                k: v for k, v in serializer.validated_data.items()
                if k != 'override_reason'
            }
            record = override_locked_record(
                record, override_reason, member, **fields
            )
        else:
            serializer.save()

        return Response({
            'message': f"Staff attendance record updated for {record.staff.full_name}.",
            'data': StaffAttendanceSerializer(record).data,
        })

    def delete(self, request, pk, *args, **kwargs):
        school = self.get_school()
        record = self.get_object(school, pk)

        if record.locked and not request.user.is_superuser:
            raise PermissionDenied(
                "Locked fingerprint records can only be deleted by a superuser."
            )

        name = record.staff.full_name
        record.delete()
        return Response({'message': f"Staff attendance record for {name} deleted."})


@extend_schema(tags=["Staff Attendance"])
class StaffAttendanceSummaryView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def get(self, request, *args, **kwargs):
        school = self.get_school()

        staff_id = request.query_params.get('staff')
        term_id = request.query_params.get('term')

        if not staff_id or not term_id:
            return Response({
                'message': 'Both staff and term query parameters are required.',
            }, status=status.HTTP_400_BAD_REQUEST)

        from apps.teachers.models import StaffProfile
        try:
            staff = StaffProfile.objects.get(pk=staff_id, school=school)
            term = Term.objects.get(pk=term_id, school=school)
        except (StaffProfile.DoesNotExist, Term.DoesNotExist):
            raise NotFound("Staff member or term not found.")

        summary = get_staff_attendance_summary(staff, term)

        return Response({
            'message': f"Attendance summary for {staff.full_name}.",
            'data': {
                'staff': staff_id,
                'staff_name': staff.full_name,
                'term': term_id,
                'term_name': str(term),
                **summary,
            },
        })


# ── Device Ingest ──────────────────────────────────────────────────────────────

@extend_schema(tags=["Device Ingest"])
class DeviceIngestView(GenericAPIView):
    """
    Endpoint for fingerprint hardware devices.
    Authenticates via device API key (X-Device-Key header), not JWT.
    Returns 202 Accepted immediately — heavy processing queued async.
    """
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = DeviceIngestSerializer

    def post(self, request, *args, **kwargs):
        # Device key authentication
        device_key = request.headers.get('X-Device-Key')
        if not device_key:
            return Response({
                'message': 'Device authentication required.',
            }, status=status.HTTP_401_UNAUTHORIZED)

        # TODO: validate device_key against a registered Device model
        # For now accept any key in dev — lock this down before production
        from django.conf import settings as django_settings
        expected_key = getattr(django_settings, 'FINGERPRINT_DEVICE_KEY', None)
        if expected_key and device_key != expected_key:
            return Response({
                'message': 'Invalid device key.',
            }, status=status.HTTP_401_UNAUTHORIZED)

        serializer = DeviceIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # TODO: Queue Celery task for async processing
        # from apps.attendance.tasks import task_process_device_ingest
        # task_process_device_ingest.delay(data)
        #
        # For Phase 1 — log the payload and return accepted
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"[DEVICE INGEST] device={data['device_id']} "
            f"fingerprint={data['fingerprint_id']} "
            f"type={data['scan_type']} "
            f"at={data['scanned_at']}"
        )

        return Response({
            'message': 'Scan received and queued for processing.',
            'data': {
                'device_id': data['device_id'],
                'fingerprint_id': data['fingerprint_id'],
                'scan_type': data['scan_type'],
                'scanned_at': str(data['scanned_at']),
            },
        }, status=status.HTTP_202_ACCEPTED)