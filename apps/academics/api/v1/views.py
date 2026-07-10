from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import extend_schema
from apps.core.renderers import IlimiAPIRenderer
from apps.tenants.models import SchoolMember
from apps.academics.models import (
    AcademicYear, Term, ClassLevel, ClassRoom, Subject, SubjectAssignment
)
from .serializers import (
    AcademicYearSerializer, AcademicYearCreateSerializer,
    TermSerializer, TermCreateSerializer,
    ClassLevelSerializer, ClassLevelCreateSerializer,
    ClassRoomSerializer, ClassRoomCreateSerializer,
    SubjectSerializer, SubjectCreateSerializer,
    SubjectAssignmentSerializer, SubjectAssignmentCreateSerializer,
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


# ── Academic Years ────────────────────────────────────────────────────────

@extend_schema(tags=["Academics"])
class AcademicYearListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = AcademicYearSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        years = AcademicYear.objects.filter(school=school)
        serializer = AcademicYearSerializer(years, many=True)
        return Response({'academic_years': serializer.data, 'count': years.count()})

    def post(self, request, *args, **kwargs):
        school = self.get_school()
        serializer = AcademicYearCreateSerializer(
            data=request.data, context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        year = serializer.save(school=school)
        return Response(
            {
                'message': f"Academic year '{year.name}' created successfully.",
                **AcademicYearSerializer(year).data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Academics"])
class AcademicYearDetailView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = AcademicYearSerializer

    def get_object(self, school, pk):
        try:
            return AcademicYear.objects.get(school=school, pk=pk)
        except AcademicYear.DoesNotExist:
            raise NotFound("Academic year not found.")

    def get(self, request, pk, *args, **kwargs):
        school = self.get_school()
        year = self.get_object(school, pk)
        return Response(AcademicYearSerializer(year).data)

    def patch(self, request, pk, *args, **kwargs):
        school = self.get_school()
        year = self.get_object(school, pk)
        serializer = AcademicYearCreateSerializer(
            year, data=request.data, partial=True, context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'Academic year updated.',
            **AcademicYearSerializer(year).data,
        })


# ── Terms ─────────────────────────────────────────────────────────────────

@extend_schema(tags=["Academics"])
class TermListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = TermSerializer

    def get_academic_year(self, school, year_pk):
        try:
            return AcademicYear.objects.get(school=school, pk=year_pk)
        except AcademicYear.DoesNotExist:
            raise NotFound("Academic year not found.")

    def get(self, request, year_pk, *args, **kwargs):
        school = self.get_school()
        academic_year = self.get_academic_year(school, year_pk)
        terms = Term.objects.filter(academic_year=academic_year)
        serializer = TermSerializer(terms, many=True)
        return Response({'terms': serializer.data, 'count': terms.count()})

    def post(self, request, year_pk, *args, **kwargs):
        school = self.get_school()
        academic_year = self.get_academic_year(school, year_pk)
        serializer = TermCreateSerializer(
            data=request.data, context={'academic_year': academic_year}
        )
        serializer.is_valid(raise_exception=True)
        term = serializer.save(academic_year=academic_year)
        return Response(
            {
                'message': f"'{term.get_name_display()}' created successfully.",
                **TermSerializer(term).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ── Class Levels ──────────────────────────────────────────────────────────

@extend_schema(tags=["Academics"])
class ClassLevelListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = ClassLevelSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        levels = ClassLevel.objects.filter(school=school, is_active=True)
        serializer = ClassLevelSerializer(levels, many=True)
        return Response({'class_levels': serializer.data, 'count': levels.count()})

    def post(self, request, *args, **kwargs):
        school = self.get_school()
        serializer = ClassLevelCreateSerializer(
            data=request.data, context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        level = serializer.save(school=school)
        return Response(
            {
                'message': f"Class level '{level.display_name}' created successfully.",
                **ClassLevelSerializer(level).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ── Classrooms ────────────────────────────────────────────────────────────

@extend_schema(tags=["Academics"])
class ClassRoomListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = ClassRoomSerializer

    def get_academic_year(self, school, year_pk):
        try:
            return AcademicYear.objects.get(school=school, pk=year_pk)
        except AcademicYear.DoesNotExist:
            raise NotFound("Academic year not found.")

    def get(self, request, year_pk, *args, **kwargs):
        school = self.get_school()
        academic_year = self.get_academic_year(school, year_pk)
        classrooms = ClassRoom.objects.filter(
            school=school, academic_year=academic_year, is_active=True
        ).select_related('class_level', 'form_teacher__user', 'branch')
        serializer = ClassRoomSerializer(classrooms, many=True)
        return Response({'classrooms': serializer.data, 'count': classrooms.count()})

    def post(self, request, year_pk, *args, **kwargs):
        school = self.get_school()
        academic_year = self.get_academic_year(school, year_pk)
        serializer = ClassRoomCreateSerializer(
            data=request.data,
            context={'school': school, 'academic_year': academic_year}
        )
        serializer.is_valid(raise_exception=True)
        classroom = serializer.save(school=school, academic_year=academic_year)
        return Response(
            {
                'message': f"Classroom '{classroom.full_name}' created successfully.",
                **ClassRoomSerializer(classroom).data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Academics"])
class ClassRoomDetailView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = ClassRoomSerializer

    def get_object(self, school, pk):
        try:
            return ClassRoom.objects.get(school=school, pk=pk)
        except ClassRoom.DoesNotExist:
            raise NotFound("Classroom not found.")

    def get(self, request, pk, *args, **kwargs):
        school = self.get_school()
        classroom = self.get_object(school, pk)
        return Response(ClassRoomSerializer(classroom).data)

    def patch(self, request, pk, *args, **kwargs):
        school = self.get_school()
        classroom = self.get_object(school, pk)
        serializer = ClassRoomCreateSerializer(
            classroom, data=request.data, partial=True,
            context={'school': school, 'academic_year': classroom.academic_year}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'Classroom updated successfully.',
            **ClassRoomSerializer(classroom).data,
        })


# ── Subjects ──────────────────────────────────────────────────────────────

@extend_schema(tags=["Academics"])
class SubjectListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = SubjectSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        subjects = Subject.objects.filter(school=school, is_active=True)
        serializer = SubjectSerializer(subjects, many=True)
        return Response({'subjects': serializer.data, 'count': subjects.count()})

    def post(self, request, *args, **kwargs):
        school = self.get_school()
        serializer = SubjectCreateSerializer(
            data=request.data, context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        subject = serializer.save(school=school)
        return Response(
            {
                'message': f"Subject '{subject.name}' created successfully.",
                **SubjectSerializer(subject).data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Academics"])
class SubjectDetailView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = SubjectSerializer

    def get_object(self, school, pk):
        try:
            return Subject.objects.get(school=school, pk=pk)
        except Subject.DoesNotExist:
            raise NotFound("Subject not found.")

    def get(self, request, pk, *args, **kwargs):
        school = self.get_school()
        subject = self.get_object(school, pk)
        return Response(SubjectSerializer(subject).data)

    def patch(self, request, pk, *args, **kwargs):
        school = self.get_school()
        subject = self.get_object(school, pk)
        serializer = SubjectCreateSerializer(
            subject, data=request.data, partial=True,
            context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'Subject updated successfully.',
            **SubjectSerializer(subject).data,
        })


# ── Subject Assignments ───────────────────────────────────────────────────

@extend_schema(tags=["Academics"])
class SubjectAssignmentListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = SubjectAssignmentSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        assignments = SubjectAssignment.objects.filter(
            classroom__school=school
        ).select_related(
            'subject', 'classroom__class_level', 'teacher__user', 'term'
        )
        serializer = SubjectAssignmentSerializer(assignments, many=True)
        return Response({'assignments': serializer.data, 'count': assignments.count()})

    def post(self, request, *args, **kwargs):
        school = self.get_school()
        serializer = SubjectAssignmentCreateSerializer(
            data=request.data, context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save()
        return Response(
            {
                'message': f"'{assignment.subject.name}' assigned successfully.",
                **SubjectAssignmentSerializer(assignment).data,
            },
            status=status.HTTP_201_CREATED,
        )

@extend_schema(tags=["Academics"])
class MySchoolClassroomsView(SchoolScopedMixin, GenericAPIView):
    """
    Returns all active classrooms for the school's current academic year,
    in one call. Used for admin filters/dropdowns where a specific
    academic year isn't already known.
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = ClassRoomSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()

        current_year = AcademicYear.objects.filter(school=school, is_current=True).first()
        if not current_year:
            return Response({'classrooms': [], 'count': 0, 'academic_year': None})

        classrooms = ClassRoom.objects.filter(
            school=school, academic_year=current_year, is_active=True
        ).select_related('class_level').order_by('class_level__order', 'section_name')

        serializer = ClassRoomSerializer(classrooms, many=True)
        return Response({
            'classrooms': serializer.data,
            'count': classrooms.count(),
            'academic_year': current_year.name,
        })