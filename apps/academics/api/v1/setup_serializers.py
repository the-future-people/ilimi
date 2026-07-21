from rest_framework import serializers

from apps.academics.models import GESCalendarTemplate, GESCalendarTermTemplate
from apps.academics.services.setup import TERM_SEQUENCE


class GESCalendarTermTemplateSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source='get_name_display', read_only=True)

    class Meta:
        model = GESCalendarTermTemplate
        fields = [
            'name', 'display_name',
            'start_date', 'end_date',
            'vacation_start_date', 'vacation_end_date',
            'midterm_start_date', 'midterm_end_date',
        ]


class GESCalendarTemplateSerializer(serializers.ModelSerializer):
    """Read-only. Templates are seeded by management command, never via API."""

    terms = GESCalendarTermTemplateSerializer(many=True, read_only=True)

    class Meta:
        model = GESCalendarTemplate
        fields = [
            'id', 'name', 'start_date', 'end_date',
            'exam_start_date', 'exam_end_date',
            'published_on', 'source_note', 'terms',
        ]


class SetupTermInputSerializer(serializers.Serializer):
    name = serializers.ChoiceField(choices=TERM_SEQUENCE)
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class AcademicYearSetupSerializer(serializers.Serializer):
    """
    Input for the one-shot year + terms setup.

    Shape validation only — coherence checks (term ordering, duplicate year
    name) live in services.setup so the service stays callable outside DRF.
    Named distinctly from the existing AcademicYearCreateSerializer, which
    creates a bare year with no terms.
    """

    name = serializers.CharField(max_length=20)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    terms = SetupTermInputSerializer(many=True)
    current_term_name = serializers.ChoiceField(
        choices=TERM_SEQUENCE, default='term_1'
    )

    def validate_terms(self, value):
        if not value:
            raise serializers.ValidationError("At least one term is required.")
        return value


from apps.academics.models import AcademicYear
from .serializers import TermSerializer


class AcademicYearWithTermsSerializer(serializers.ModelSerializer):
    """
    Year plus its nested terms and a resolved current_term.

    Separate from the existing AcademicYearSerializer, which is flat and
    consumed elsewhere — widening that one would change payloads for
    callers that don't need terms.
    """

    terms = TermSerializer(many=True, read_only=True)
    current_term = serializers.SerializerMethodField()

    class Meta:
        model = AcademicYear
        fields = [
            'id', 'name', 'start_date', 'end_date',
            'is_current', 'terms', 'current_term',
        ]

    def get_current_term(self, obj):
        term = next((t for t in obj.terms.all() if t.is_current), None)
        return TermSerializer(term).data if term else None