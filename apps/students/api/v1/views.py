from django.db import transaction
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import extend_schema

from apps.core.renderers import IlimiAPIRenderer
from apps.tenants.models import SchoolMember
from apps.academics.models import AcademicYear
from apps.students.models import (
    Student,
    Guardian,
    StudentGuardian,
    EmergencyContact,
    StudentClassHistory,
)
from .serializers import (
    StudentSerializer,
    StudentListSerializer,
    StudentEnrolSerializer,
    StudentUpdateSerializer,
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
            'current_class', 'branch'
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
        if search:
            qs = qs.filter(first_name__icontains=search) | \
                 qs.filter(last_name__icontains=search) | \
                 qs.filter(student_id__icontains=search)

        qs = qs.order_by('last_name', 'first_name')
        serializer = StudentListSerializer(qs, many=True)
        return Response({'students': serializer.data, 'count': qs.count()})

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        member = self.get_member()
        school = member.school
        branch = member.branch

        serializer = StudentEnrolSerializer(
            data=request.data, context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        guardians_data = data.pop('guardians')
        emergency_contacts_data = data.pop('emergency_contacts', [])

        student = Student.objects.create(
            school=school,
            branch=branch,
            **data,
        )

        for g_data in guardians_data:
            is_primary = g_data.pop('is_primary', False)
            guardian = Guardian.objects.create(**g_data)
            StudentGuardian.objects.create(
                student=student,
                guardian=guardian,
                is_primary=is_primary,
            )

        for ec_data in emergency_contacts_data:
            EmergencyContact.objects.create(student=student, **ec_data)

        try:
            current_year = AcademicYear.objects.get(school=school, is_current=True)
            if student.current_class:
                StudentClassHistory.objects.create(
                    student=student,
                    classroom=student.current_class,
                    academic_year=current_year,
                    is_current=True,
                )
        except AcademicYear.DoesNotExist:
            pass

        from apps.students.services.notification_service import notify_guardian_enrolment
        notify_guardian_enrolment(student, school)

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