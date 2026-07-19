from django.db import transaction
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import extend_schema

from apps.core.models.occupation import Occupation
from apps.core.renderers import IlimiAPIRenderer
from apps.tenants.models import SchoolMember
from apps.academics.models import AcademicYear
from django.db.models import F, Prefetch
from django.utils import timezone
from datetime import timedelta
from rest_framework.permissions import AllowAny
from apps.students.models import (
    Student,
    Guardian,
    StudentGuardian,
    EmergencyContact,
    StudentClassHistory,
    EnrolmentInvite,
)
from .serializers import (
    StudentSerializer,
    StudentListSerializer,
    StudentEnrolSerializer,
    StudentUpdateSerializer,
    EnrolmentInviteCreateSerializer,
    EnrolmentInviteListSerializer,
    EnrolmentInvitePublicSerializer,
    EnrolmentInviteSubmissionSerializer,
    StudentGuardianSerializer,
    GuardianCreateSerializer,
    EmergencyContactSerializer,
    EmergencyContactCreateSerializer,
    StudentClassHistorySerializer,
)


# ── Mixin ─────────────────────────────────────────────────────────────────

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
        ).select_related('school', 'branch').first()
        if not member:
            raise NotFound("No school found for your account.")
        return member


# ── Students List + Enrol ─────────────────────────────────────────────────

@extend_schema(tags=["Students"])
class StudentListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = StudentSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        qs = Student.objects.filter(school=school).select_related(
            'current_class__class_level', 'branch'
        ).prefetch_related(
            Prefetch(
                'student_guardians',
                queryset=StudentGuardian.objects.select_related('guardian').order_by('-is_primary'),
            )
        )

        classroom_id = request.query_params.get('classroom')
        status_filter = request.query_params.get('status')
        branch_id = request.query_params.get('branch')
        search = request.query_params.get('search')

        if classroom_id:
            qs = qs.filter(current_class_id=classroom_id)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)

        unassigned = request.query_params.get('unassigned')
        exclude_unassigned = request.query_params.get('exclude_unassigned')
        if unassigned == 'true':
            qs = qs.filter(current_class__isnull=True)
        elif exclude_unassigned == 'true':
            qs = qs.filter(current_class__isnull=False)

        missing_fingerprint = request.query_params.get('missing_fingerprint')
        if missing_fingerprint == 'true':
            qs = qs.filter(fingerprint_data='')

        if search:
            qs = qs.filter(first_name__icontains=search) | \
                 qs.filter(last_name__icontains=search) | \
                 qs.filter(student_id__icontains=search)

        sort_dir = request.query_params.get('sort_dir', 'asc')
        name_order = ('last_name', 'first_name') if sort_dir == 'asc' else ('-last_name', '-first_name')

        qs = qs.order_by(
            F('current_class__class_level__order').desc(nulls_last=True),
            'current_class__section_name', *name_order,
        )

        total_count = qs.count()

        try:
            page = max(int(request.query_params.get('page', 1)), 1)
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(max(int(request.query_params.get('page_size', 20)), 1), 100)
        except (TypeError, ValueError):
            page_size = 20

        start = (page - 1) * page_size
        end = start + page_size
        page_qs = qs[start:end]

        serializer = StudentListSerializer(page_qs, many=True)
        return Response({
            'students': serializer.data,
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size if total_count else 0,
            'has_next': end < total_count,
            'has_previous': page > 1,
        })
    

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        member = self.get_member()
        school = member.school
        branch = member.branch

        serializer = StudentEnrolSerializer(
            data=request.data, context={'school': school}
        )
        serializer.is_valid(raise_exception=True)

        from apps.students.services.enrolment import create_student_with_guardians
        student = create_student_with_guardians(school, branch, serializer.validated_data)

        return Response(
            {
                'message': f"Student '{student.first_name} {student.last_name}' enrolled successfully.",
                **StudentSerializer(student).data,
            },
            status=status.HTTP_201_CREATED,
        )

# ── Student Detail + Update ───────────────────────────────────────────────

@extend_schema(tags=["Students"])
class StudentDetailView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = StudentSerializer

    def get_object(self, school, pk):
        try:
            return Student.objects.get(school=school, pk=pk)
        except Student.DoesNotExist:
            raise NotFound("Student not found.")

    def get(self, request, pk, *args, **kwargs):
        school = self.get_school()
        student = self.get_object(school, pk)
        return Response(StudentSerializer(student).data)

    def patch(self, request, pk, *args, **kwargs):
        school = self.get_school()
        student = self.get_object(school, pk)
        serializer = StudentUpdateSerializer(
            student, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'Student updated successfully.',
            **StudentSerializer(student).data,
        })


# ── Guardians ─────────────────────────────────────────────────────────────
ALLOWED_STUDENT_UPLOAD_FIELDS = {'photo', 'fingerprint_data'}
ALLOWED_GUARDIAN_UPLOAD_FIELDS = {'photo', 'fingerprint_data', 'ghana_card_front', 'ghana_card_back'}


@extend_schema(tags=["Students"])
class StudentFileUploadView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = None

    def post(self, request, pk, field, *args, **kwargs):
        school = self.get_school()

        if field not in ALLOWED_STUDENT_UPLOAD_FIELDS:
            return Response(
                {"status": "error", "message": f"Field '{field}' is not uploadable.", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            student = Student.objects.get(school=school, pk=pk)
        except Student.DoesNotExist:
            raise NotFound("Student not found.")

        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {"status": "error", "message": "No file provided.", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        setattr(student, field, file_obj)
        student.save(update_fields=[field])

        file_field = getattr(student, field)
        return Response({
            'field': field,
            'url': file_field.url if file_field else None,
        })


@extend_schema(tags=["Students"])
class GuardianFileUploadView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = None

    def post(self, request, pk, field, *args, **kwargs):
        school = self.get_school()

        if field not in ALLOWED_GUARDIAN_UPLOAD_FIELDS:
            return Response(
                {"status": "error", "message": f"Field '{field}' is not uploadable.", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        link_exists = StudentGuardian.objects.filter(
            guardian_id=pk, student__school=school
        ).exists()
        if not link_exists:
            raise NotFound("Guardian not found.")

        try:
            guardian = Guardian.objects.get(pk=pk)
        except Guardian.DoesNotExist:
            raise NotFound("Guardian not found.")

        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {"status": "error", "message": "No file provided.", "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        setattr(guardian, field, file_obj)
        guardian.save(update_fields=[field])

        file_field = getattr(guardian, field)
        return Response({
            'field': field,
            'url': file_field.url if file_field else None,
        })
    
@extend_schema(tags=["Students"])
class StudentGuardianListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = StudentGuardianSerializer

    def get_student(self, school, pk):
        try:
            return Student.objects.get(school=school, pk=pk)
        except Student.DoesNotExist:
            raise NotFound("Student not found.")

    def get(self, request, pk, *args, **kwargs):
        school = self.get_school()
        student = self.get_student(school, pk)
        links = StudentGuardian.objects.filter(student=student).select_related('guardian')
        serializer = StudentGuardianSerializer(links, many=True)
        return Response({'guardians': serializer.data, 'count': links.count()})

    @transaction.atomic
    def post(self, request, pk, *args, **kwargs):
        school = self.get_school()
        student = self.get_student(school, pk)
        serializer = GuardianCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        is_primary = data.pop('is_primary', False)
        guardian = Guardian.objects.create(**data)
        link = StudentGuardian.objects.create(
            student=student,
            guardian=guardian,
            is_primary=is_primary,
        )

        return Response(
            {
                'message': f"Guardian '{guardian.first_name} {guardian.last_name}' added successfully.",
                **StudentGuardianSerializer(link).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ── Emergency Contacts ────────────────────────────────────────────────────

@extend_schema(tags=["Students"])
class StudentEmergencyContactView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = EmergencyContactSerializer

    def get_student(self, school, pk):
        try:
            return Student.objects.get(school=school, pk=pk)
        except Student.DoesNotExist:
            raise NotFound("Student not found.")

    def post(self, request, pk, *args, **kwargs):
        school = self.get_school()
        student = self.get_student(school, pk)
        serializer = EmergencyContactCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = EmergencyContact.objects.create(
            student=student, **serializer.validated_data
        )
        return Response(
            {
                'message': f"Emergency contact '{contact.full_name}' added successfully.",
                **EmergencyContactSerializer(contact).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ── Class History ─────────────────────────────────────────────────────────

@extend_schema(tags=["Students"])
class StudentClassHistoryView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = StudentClassHistorySerializer

    def get(self, request, pk, *args, **kwargs):
        school = self.get_school()
        try:
            student = Student.objects.get(school=school, pk=pk)
        except Student.DoesNotExist:
            raise NotFound("Student not found.")

        history = StudentClassHistory.objects.filter(
            student=student
        ).select_related(
            'classroom', 'academic_year'
        ).order_by('-academic_year__start_date')

        serializer = StudentClassHistorySerializer(history, many=True)
        return Response({'history': serializer.data, 'count': history.count()})


@extend_schema(tags=["Students"])
class StudentChangeClassView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    @transaction.atomic
    def post(self, request, pk, *args, **kwargs):
        from apps.academics.models import ClassRoom, AcademicYear

        school = self.get_school()

        try:
            student = Student.objects.get(school=school, pk=pk)
        except Student.DoesNotExist:
            raise NotFound("Student not found.")

        classroom_id = request.data.get('classroom_id')
        remarks = request.data.get('remarks', '')

        if not classroom_id:
            return Response({'message': 'classroom_id is required.'}, status=400)

        try:
            classroom = ClassRoom.objects.get(id=classroom_id, school=school)
        except ClassRoom.DoesNotExist:
            return Response({'message': 'Classroom not found.'}, status=400)

        current_year = AcademicYear.objects.filter(school=school, is_current=True).first()
        if not current_year:
            return Response({'message': 'No active academic year found for this school.'}, status=400)

        old_classroom_name = student.current_class.full_name if student.current_class else 'Unassigned'

        # Mark any existing current history row as no longer current
        StudentClassHistory.objects.filter(
            student=student, is_current=True
        ).update(is_current=False)

        # Create the new history row
        StudentClassHistory.objects.create(
            student=student,
            classroom=classroom,
            academic_year=current_year,
            is_current=True,
            remarks=remarks,
        )

        # Update the student's current class
        student.current_class = classroom
        student.save(update_fields=['current_class'])

        return Response({
            'message': f"{student.full_name} moved from {old_classroom_name} to {classroom.full_name}.",
            **StudentSerializer(student).data,
        })

@extend_schema(tags=["Students"])
class StudentBulkChangeClassView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        from apps.academics.models import ClassRoom, AcademicYear

        school = self.get_school()

        student_ids = request.data.get('student_ids', [])
        classroom_id = request.data.get('classroom_id')
        remarks = request.data.get('remarks', '')

        if not student_ids:
            return Response({'message': 'student_ids is required and cannot be empty.'}, status=400)
        if not classroom_id:
            return Response({'message': 'classroom_id is required.'}, status=400)

        try:
            classroom = ClassRoom.objects.get(id=classroom_id, school=school)
        except ClassRoom.DoesNotExist:
            return Response({'message': 'Classroom not found.'}, status=400)

        current_year = AcademicYear.objects.filter(school=school, is_current=True).first()
        if not current_year:
            return Response({'message': 'No active academic year found for this school.'}, status=400)

        students = Student.objects.filter(id__in=student_ids, school=school)
        found_ids = set(students.values_list('id', flat=True))
        missing_ids = set(student_ids) - found_ids

        moved = []
        for student in students:
            StudentClassHistory.objects.filter(
                student=student, is_current=True
            ).update(is_current=False)

            StudentClassHistory.objects.create(
                student=student,
                classroom=classroom,
                academic_year=current_year,
                is_current=True,
                remarks=remarks,
            )

            student.current_class = classroom
            student.save(update_fields=['current_class'])
            moved.append(student.full_name)

        response_data = {
            'message': f"{len(moved)} student(s) moved to {classroom.full_name}.",
            'moved_count': len(moved),
            'moved_students': moved,
        }

        if missing_ids:
            response_data['warning'] = f"{len(missing_ids)} student ID(s) not found or do not belong to your school."
            response_data['missing_ids'] = list(missing_ids)

        return Response(response_data)

# ── Enrolment Invites (Admin) ───────────────────────────────────────────────

@extend_schema(tags=["Students"])
class EnrolmentInviteListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = EnrolmentInviteListSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        qs = EnrolmentInvite.objects.filter(school=school).select_related(
            'invited_by__user'
        )
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        serializer = EnrolmentInviteListSerializer(qs, many=True)
        return Response({'invites': serializer.data, 'count': qs.count()})

    def post(self, request, *args, **kwargs):
        member = self.get_member()
        serializer = EnrolmentInviteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invite = EnrolmentInvite.objects.create(
            school=member.school,
            invited_by=member,
            expires_at=timezone.now() + timedelta(hours=72),
            **serializer.validated_data,
        )

        try:
            from apps.notifications.services.sms import send_sms
            link = f"{request.scheme}://{request.get_host()}/enrol/{invite.token}"
            send_sms(
                invite.parent_phone,
                f"{member.school.name}: Please complete {invite.prospective_full_name}'s "
                f"enrolment form here: {link} (link expires in 72 hours)",
            )
        except Exception:
            pass  # SMS failure shouldn't block invite creation; link still works if copied manually

        return Response(
            {
                'message': f"Invite sent for {invite.prospective_full_name}.",
                **EnrolmentInviteListSerializer(invite).data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Students"])
class EnrolmentInviteApproveView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    @transaction.atomic
    def post(self, request, pk, *args, **kwargs):
        school = self.get_school()
        member = self.get_member()

        try:
            invite = EnrolmentInvite.objects.get(school=school, pk=pk)
        except EnrolmentInvite.DoesNotExist:
            raise NotFound("Invite not found.")

        if invite.status != 'submitted':
            return Response(
                {'message': f"Invite is '{invite.status}', not ready for approval."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Admin can override/patch fields (e.g. assign a classroom) at approval time
        payload = dict(invite.submitted_data or {})
        payload.update(request.data.get('overrides', {}))

        enrol_serializer = StudentEnrolSerializer(data=payload, context={'school': school})
        enrol_serializer.is_valid(raise_exception=True)

        from apps.students.services.enrolment import create_student_with_guardians
        student = create_student_with_guardians(
            school, member.branch, enrol_serializer.validated_data
        )

        if invite.submitted_photo:
            student.photo.save(
                invite.submitted_photo.name.split('/')[-1],
                invite.submitted_photo.file,
                save=True,
            )

        invite.status = 'approved'
        invite.reviewed_by = member
        invite.created_student = student
        invite.save(update_fields=['status', 'reviewed_by', 'created_student'])

        return Response({
            'message': f"{student.full_name} enrolled successfully.",
            **StudentSerializer(student).data,
        })


@extend_schema(tags=["Students"])
class EnrolmentInviteRejectView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, pk, *args, **kwargs):
        school = self.get_school()
        member = self.get_member()

        try:
            invite = EnrolmentInvite.objects.get(school=school, pk=pk)
        except EnrolmentInvite.DoesNotExist:
            raise NotFound("Invite not found.")

        invite.status = 'rejected'
        invite.reviewed_by = member
        invite.review_remarks = request.data.get('remarks', '')
        invite.save(update_fields=['status', 'reviewed_by', 'review_remarks'])

        return Response({'message': 'Invite rejected.'})


# ── Enrolment Invites (Public, unauthenticated) ─────────────────────────────

@extend_schema(tags=["Students"])
class PublicEnrolmentInviteDetailView(GenericAPIView):
    permission_classes = [AllowAny]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = EnrolmentInvitePublicSerializer

    def get(self, request, token, *args, **kwargs):
        try:
            invite = EnrolmentInvite.objects.select_related('school').get(token=token)
        except (EnrolmentInvite.DoesNotExist, ValueError):
            raise NotFound("This enrolment link is invalid.")

        if invite.status != 'pending':
            return Response(
                {'message': 'This enrolment link has already been used.'},
                status=status.HTTP_410_GONE,
            )
        if invite.is_expired:
            invite.status = 'expired'
            invite.save(update_fields=['status'])
            return Response(
                {'message': 'This enrolment link has expired. Please contact the school for a new one.'},
                status=status.HTTP_410_GONE,
            )

        return Response(EnrolmentInvitePublicSerializer({
            'school_name': invite.school.name,
            'prospective_first_name': invite.prospective_first_name,
            'prospective_last_name': invite.prospective_last_name,
        }).data)


@extend_schema(tags=["Students"])
class PublicEnrolmentInviteSubmitView(GenericAPIView):
    permission_classes = [AllowAny]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = EnrolmentInviteSubmissionSerializer

    def post(self, request, token, *args, **kwargs):
        try:
            invite = EnrolmentInvite.objects.get(token=token)
        except (EnrolmentInvite.DoesNotExist, ValueError):
            raise NotFound("This enrolment link is invalid.")

        if invite.status != 'pending':
            return Response(
                {'message': 'This enrolment link has already been used.'},
                status=status.HTTP_410_GONE,
            )
        if invite.is_expired:
            invite.status = 'expired'
            invite.save(update_fields=['status'])
            return Response(
                {'message': 'This enrolment link has expired.'},
                status=status.HTTP_410_GONE,
            )

        import json
        data = {}
        for key in request.data.keys():
            value = request.data.get(key)
            if key in ('guardians', 'emergency_contacts') and isinstance(value, str):
                try:
                    value = json.loads(value)
                except (ValueError, TypeError):
                    value = []
            data[key] = value

        serializer = EnrolmentInviteSubmissionSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        invite.submitted_data = serializer.validated_data
        invite.status = 'submitted'
        invite.submitted_at = timezone.now()

        photo = request.FILES.get('photo')
        if photo:
            invite.submitted_photo = photo

        invite.save(update_fields=['submitted_data', 'status', 'submitted_at', 'submitted_photo'])

        return Response({'message': 'Thank you — your submission has been received.'})