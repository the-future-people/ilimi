from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from apps.tenants.models import School
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.academics.models import AcademicYear, GESCalendarTemplate
from apps.academics.services.setup import (
    create_academic_year_with_terms,
    suggest_calendar_and_term,
)
from apps.core.renderers import IlimiAPIRenderer

from .setup_serializers import (
    AcademicYearSetupSerializer,
    AcademicYearWithTermsSerializer,
    GESCalendarTemplateSerializer,
)
from .views import SchoolScopedMixin


@extend_schema(tags=["Academics"])
class GESCalendarTemplateListView(SchoolScopedMixin, GenericAPIView):
    """
    Published GES calendars available to pre-fill academic year setup.

    Also returns which year and term to pre-select. The suggestion is
    advisory — a school onboarding in the last week of a term is usually
    preparing for the next one, and that intent isn't derivable from dates,
    so the setup form shows both as editable.
    """

    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = GESCalendarTemplateSerializer

    def get(self, request, *args, **kwargs):
        self.get_school()  # scope check only

        templates = GESCalendarTemplate.objects.filter(
            is_active=True
        ).prefetch_related('terms').order_by('-start_date')

        suggested_template, suggested_term = suggest_calendar_and_term(
            timezone.localdate()
        )

        return Response({
            'calendars': GESCalendarTemplateSerializer(templates, many=True).data,
            'count': templates.count(),
            'suggested_calendar_id': (
                suggested_template.id if suggested_template else None
            ),
            'suggested_term': suggested_term,
        })


@extend_schema(tags=["Academics"])
class AcademicYearSetupView(SchoolScopedMixin, GenericAPIView):
    """
    One-shot setup: creates an AcademicYear and all its Terms atomically.

    Distinct from AcademicYearListCreateView's POST, which creates a bare
    year with no terms. This is the endpoint a brand-new school hits before
    it can create any classroom.
    """

    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = AcademicYearSetupSerializer

    def get(self, request, *args, **kwargs):
        """
        What this school still needs before it can run.

        Three things block a school from functioning: a curriculum, an
        academic year, and classes. Staff, assignments and students are
        reported alongside so the portal can nudge, but a school adds
        those at its own pace.
        """
        from apps.academics.models import ClassRoom, SubjectAssignment
        from apps.teachers.models import StaffProfile
        from apps.students.models import Student

        school = self.get_school()
        current = AcademicYear.objects.filter(
            school=school, is_current=True
        ).prefetch_related('terms').first()

        has_year = current is not None
        classrooms = ClassRoom.objects.filter(
            school=school, is_active=True
        ).count() if has_year else 0
        staff = StaffProfile.objects.filter(school=school).count()
        assignments = SubjectAssignment.objects.filter(
            classroom__school=school
        ).count()
        students = Student.objects.filter(school=school, status='active').count()

        # Only these three block a school from functioning. Staff,
        # assignments and students are reported so the portal can nudge,
        # but a school is free to add them at its own pace.
        steps = [
            {'key': 'curriculum', 'label': 'Confirm your curriculum',
             'done': bool(school.curriculum), 'count': None,
             'value': school.get_curriculum_display()},
            {'key': 'academic_year', 'label': 'Set up the academic year',
             'done': has_year, 'count': None,
             'value': current.name if current else None},
            {'key': 'classes', 'label': 'Create your classes',
             'done': classrooms > 0, 'count': classrooms, 'value': None},
        ]

        progress = {
            'staff': staff,
            'assignments': assignments,
            'students': students,
        }
        return Response({
            'needs_setup': current is None,
            'academic_year': (
                AcademicYearWithTermsSerializer(current).data if current else None
            ),
            'steps': steps,
            'progress': progress,
            'curriculum': school.curriculum,
            'curriculum_supported': school.curriculum in School.CURRICULUM_SUPPORTED,
            'setup_complete': all(s['done'] for s in steps),
        })

    def post(self, request, *args, **kwargs):
        school = self.get_school()

        serializer = AcademicYearSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            year = create_academic_year_with_terms(
                school=school,
                name=data['name'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                terms=data['terms'],
                current_term_name=data['current_term_name'],
            )
        except DjangoValidationError as exc:
            # Service layer raises Django's ValidationError so it stays
            # usable outside DRF; translate at the boundary.
            messages = exc.messages if hasattr(exc, 'messages') else [str(exc)]
            raise DRFValidationError(' '.join(messages))

        year = AcademicYear.objects.prefetch_related('terms').get(pk=year.pk)

        return Response(
            {
                'message': f"Academic year '{year.name}' set up successfully.",
                **AcademicYearWithTermsSerializer(year).data,
            },
            status=status.HTTP_201_CREATED,
        )