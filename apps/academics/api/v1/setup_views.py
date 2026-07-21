from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
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
        """Whether this school still needs setup — drives the Classes tab state."""
        school = self.get_school()
        current = AcademicYear.objects.filter(
            school=school, is_current=True
        ).prefetch_related('terms').first()

        return Response({
            'needs_setup': current is None,
            'academic_year': (
                AcademicYearWithTermsSerializer(current).data if current else None
            ),
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