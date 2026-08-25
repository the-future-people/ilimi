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
    AcademicYearSerializer, AcademicYearCreateSerializer, LessonPlanSerializer,
    TermSerializer, TermCreateSerializer,
    ClassLevelSerializer, ClassLevelCreateSerializer,
    ClassRoomSerializer, ClassRoomCreateSerializer,
    SubjectSerializer, SubjectCreateSerializer,
    SubjectAssignmentSerializer, SubjectAssignmentCreateSerializer,
    LessonPlanListSerializer, LessonPlanDaySerializer,
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
            raise NotFound("No active school found for your account.")
        return member


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
        return Response({
            'class_levels': serializer.data,
            'count': levels.count(),
            # The full GES ladder, so the frontend never hardcodes a copy of
            # LEVEL_CHOICES. Ordered by ClassLevel.LEVEL_ORDER, which is the
            # single source of truth for class seniority.
            'available_levels': [
                {
                    'name': value,
                    'display_name': label,
                    'order': ClassLevel.LEVEL_ORDER.get(value, 999),
                }
                for value, label in ClassLevel.LEVEL_CHOICES
            ],
        })

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

@extend_schema(tags=["Classrooms"])
class ClassTeacherView(SchoolScopedMixin, GenericAPIView):
    """
    Lower-band classes (Nursery to Primary 3) have one teacher for every
    subject. Sets that teacher across all core subjects and makes them
    form master, in one action.

    POST { "teacher": <school_member_id>, "term": <term_id> }
    """

    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, pk, *args, **kwargs):
        from apps.academics.models import Term
        from apps.academics.services.assignment_service import set_class_teacher
        from apps.tenants.models import SchoolMember

        school = self.get_school()

        try:
            classroom = ClassRoom.objects.select_related(
                'class_level', 'academic_year'
            ).get(school=school, pk=pk)
        except ClassRoom.DoesNotExist:
            raise NotFound("Classroom not found.")

        if classroom.class_level.band != 'lower':
            return Response({
                'message': (
                    f'{classroom.full_name} uses subject teachers. '
                    f'Assign each subject individually.'
                )
            }, status=400)

        teacher_id = request.data.get('teacher')
        term_id = request.data.get('term')

        try:
            term = Term.objects.get(id=term_id, academic_year=classroom.academic_year)
        except Term.DoesNotExist:
            return Response({'message': 'Invalid term.'}, status=400)

        teacher = None
        if teacher_id:
            try:
                teacher = SchoolMember.objects.get(
                    id=teacher_id, school=school, is_active=True
                )
            except SchoolMember.DoesNotExist:
                return Response({'message': 'Teacher not found.'}, status=400)

        created, reassigned = set_class_teacher(
            school=school,
            classroom=classroom,
            teacher=teacher,
            term=term,
        )

        name = teacher.user.full_name if teacher else None
        return Response({
            'message': (
                f'{name} now takes every subject in {classroom.full_name}.'
                if name else f'Class teacher cleared for {classroom.full_name}.'
            ),
            'created': created,
            'reassigned': reassigned,
            'classroom': ClassRoomSerializer(classroom).data,
        })


# ── Subjects ──────────────────────────────────────────────────────────────

@extend_schema(tags=["Academics"])
class SubjectListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = SubjectSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        subjects = Subject.objects.filter(
        school=school, is_active=True, subject_type='core'
    )
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

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        assignments = SubjectAssignment.objects.filter(
            classroom__school=school
        ).select_related(
            'subject', 'classroom__class_level', 'teacher__user', 'term'
        )

        classroom_id = request.query_params.get('classroom')
        if classroom_id:
            assignments = assignments.filter(classroom_id=classroom_id)

        term_id = request.query_params.get('term')
        if term_id:
            assignments = assignments.filter(term_id=term_id)

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
class SubjectAssignmentDetailView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = SubjectAssignmentSerializer

    def get_object(self, school, pk):
        try:
            return SubjectAssignment.objects.get(classroom__school=school, pk=pk)
        except SubjectAssignment.DoesNotExist:
            raise NotFound("Assignment not found.")

    def patch(self, request, pk, *args, **kwargs):
        school = self.get_school()
        assignment = self.get_object(school, pk)
        serializer = SubjectAssignmentCreateSerializer(
            assignment, data=request.data, partial=True, context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'Assignment updated.',
            **SubjectAssignmentSerializer(assignment).data,
        })

    def delete(self, request, pk, *args, **kwargs):
        school = self.get_school()
        assignment = self.get_object(school, pk)
        assignment.delete()
        return Response({'message': 'Assignment removed.'}, status=status.HTTP_204_NO_CONTENT)


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
            'academic_year_id': current_year.id,
        })

@extend_schema(tags=["Lesson Plans"])
class LessonPlanListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = LessonPlanListSerializer

    def get(self, request, *args, **kwargs):
        from apps.academics.models import LessonPlan

        member = self.get_member()
        qs = LessonPlan.objects.filter(school=member.school).select_related(
            'subject', 'classroom', 'classroom__class_level', 'facilitator__user'
        ).prefetch_related('days')

        # Teachers see only their own; vetters see everything.
        from apps.tenants.permissions import can_vet_lesson_plans
        if not can_vet_lesson_plans(member):
            qs = qs.filter(facilitator=member)

        for param, field in (
            ('classroom', 'classroom_id'),
            ('subject', 'subject_id'),
            ('term', 'term_id'),
            ('status', 'status'),
        ):
            value = request.query_params.get(param)
            if value:
                qs = qs.filter(**{field: value})

        serializer = LessonPlanListSerializer(qs, many=True)
        return Response({'lesson_plans': serializer.data, 'count': qs.count()})

    def post(self, request, *args, **kwargs):
        from apps.academics.models import ClassRoom, Subject, Term
        from apps.academics.services.lesson_plan_service import create_lesson_plan

        member = self.get_member()
        school = member.school
        data = request.data

        try:
            classroom = ClassRoom.objects.get(id=data.get('classroom'), school=school)
            subject = Subject.objects.get(id=data.get('subject'), school=school)
            term = Term.objects.get(id=data.get('term'))
        except (ClassRoom.DoesNotExist, Subject.DoesNotExist, Term.DoesNotExist):
            return Response({'message': 'Invalid classroom, subject or term.'}, status=400)

        week_ending = data.get('week_ending')
        if not week_ending:
            return Response({'message': 'Give the week ending date.'}, status=400)

        from apps.academics.models import LessonPlan
        if LessonPlan.objects.filter(
            classroom=classroom, subject=subject, term=term, week_ending=week_ending
        ).exists():
            return Response({
                'message': f'A plan already exists for {subject.name} in {classroom.full_name} that week.'
            }, status=400)

        plan = create_lesson_plan(
            school=school,
            branch=member.branch,
            classroom=classroom,
            subject=subject,
            term=term,
            week_ending=week_ending,
            facilitator=member,
            class_size=data.get('class_size') or None,
            strand=data.get('strand', ''),
            sub_strand=data.get('sub_strand', ''),
            indicator_code=data.get('indicator_code', ''),
            content_standard_code=data.get('content_standard_code', ''),
            performance_indicator=data.get('performance_indicator', ''),
            core_competencies=data.get('core_competencies', ''),
            key_words=data.get('key_words', ''),
            tlr=data.get('tlr', ''),
            reference=data.get('reference', ''),
        )

        return Response({
            'message': f'Plan started for week ending {plan.week_ending}.',
            'lesson_plan': LessonPlanSerializer(plan).data,
        }, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Lesson Plans"])
class LessonPlanDetailView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = LessonPlanSerializer

    def get_object(self, member, pk):
        from apps.academics.models import LessonPlan
        from apps.tenants.permissions import can_vet_lesson_plans

        try:
            plan = LessonPlan.objects.select_related(
                'subject', 'classroom', 'facilitator__user', 'vetted_by__user'
            ).prefetch_related('days').get(pk=pk, school=member.school)
        except LessonPlan.DoesNotExist:
            raise NotFound("Lesson plan not found.")

        if plan.facilitator_id != member.id and not can_vet_lesson_plans(member):
            raise NotFound("Lesson plan not found.")

        return plan

    def get(self, request, pk, *args, **kwargs):
        member = self.get_member()
        return Response(LessonPlanSerializer(self.get_object(member, pk)).data)

    def patch(self, request, pk, *args, **kwargs):
        member = self.get_member()
        plan = self.get_object(member, pk)

        if plan.facilitator_id != member.id:
            return Response({'message': 'Only the facilitator can edit this plan.'}, status=403)
        if not plan.is_editable:
            return Response({
                'message': 'This plan has been submitted and can no longer be edited.'
            }, status=400)

        serializer = LessonPlanSerializer(plan, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'Saved.', 'lesson_plan': serializer.data})


@extend_schema(tags=["Lesson Plans"])
class LessonPlanDayUpdateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = LessonPlanDaySerializer

    def patch(self, request, pk, *args, **kwargs):
        from apps.academics.models import LessonPlanDay

        member = self.get_member()
        try:
            day = LessonPlanDay.objects.select_related('plan').get(
                pk=pk, plan__school=member.school
            )
        except LessonPlanDay.DoesNotExist:
            raise NotFound("Day not found.")

        if day.plan.facilitator_id != member.id:
            return Response({'message': 'Only the facilitator can edit this plan.'}, status=403)
        if not day.plan.is_editable:
            return Response({'message': 'This plan can no longer be edited.'}, status=400)

        serializer = LessonPlanDaySerializer(day, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'Saved.', 'day': serializer.data})


@extend_schema(tags=["Lesson Plans"])
class LessonPlanSubmitView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, pk, *args, **kwargs):
        from apps.academics.models import LessonPlan
        from apps.academics.services.lesson_plan_service import submit_lesson_plan

        member = self.get_member()
        try:
            plan = LessonPlan.objects.get(pk=pk, school=member.school)
        except LessonPlan.DoesNotExist:
            raise NotFound("Lesson plan not found.")

        try:
            submit_lesson_plan(plan, member)
        except ValueError as e:
            return Response({'message': str(e)}, status=400)

        return Response({
            'message': 'Submitted for vetting.',
            'lesson_plan': LessonPlanSerializer(plan).data,
        })


@extend_schema(tags=["Lesson Plans"])
class LessonPlanVetView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, pk, *args, **kwargs):
        from apps.academics.models import LessonPlan
        from apps.academics.services.lesson_plan_service import vet_lesson_plan

        member = self.get_member()
        try:
            plan = LessonPlan.objects.select_related('facilitator__user').get(
                pk=pk, school=member.school
            )
        except LessonPlan.DoesNotExist:
            raise NotFound("Lesson plan not found.")

        approved = bool(request.data.get('approved'))
        remarks = request.data.get('remarks', '')

        try:
            vet_lesson_plan(plan, member, approved=approved, remarks=remarks)
        except PermissionError as e:
            return Response({'message': str(e)}, status=403)
        except ValueError as e:
            return Response({'message': str(e)}, status=400)

        return Response({
            'message': 'Plan vetted.' if approved else 'Plan returned for revision.',
            'lesson_plan': LessonPlanSerializer(plan).data,
        })