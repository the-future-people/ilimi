from rest_framework import serializers

from apps.communications.models import Excursion, ConsentRequest
from apps.students.models import Student, Guardian


class ExcursionSerializer(serializers.ModelSerializer):
    classroom_names = serializers.SerializerMethodField()
    consent_summary = serializers.SerializerMethodField()

    class Meta:
        model = Excursion
        fields = [
            'id', 'name', 'description', 'location', 'date',
            'classrooms', 'classroom_names', 'consent_summary', 'created_at',
        ]

    def get_classroom_names(self, obj):
        return [c.full_name for c in obj.classrooms.all()]

    def get_consent_summary(self, obj):
        requests = obj.consent_requests.all()
        return {
            'total': len(requests),
            'granted': sum(1 for r in requests if r.status == 'granted'),
            'denied': sum(1 for r in requests if r.status == 'denied'),
            'pending': sum(1 for r in requests if r.status == 'pending'),
        }


class ExcursionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Excursion
        fields = ['name', 'description', 'location', 'date', 'classrooms']


class ConsentRequestListSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    student_id_number = serializers.CharField(source='student.student_id', read_only=True)
    classroom_name = serializers.CharField(source='student.current_class.full_name', read_only=True)
    current_class_id = serializers.IntegerField(source='student.current_class.id', read_only=True)
    class_level_order = serializers.IntegerField(source='student.current_class.class_level.order', read_only=True)
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    excursion_name = serializers.CharField(source='excursion.name', read_only=True)
    consent_type_display = serializers.CharField(source='get_consent_type_display', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = ConsentRequest
        fields = [
            'id', 'student', 'student_name', 'student_id_number',
            'classroom_name', 'current_class_id', 'class_level_order',
            'guardian', 'guardian_name', 'consent_type', 'consent_type_display',
            'excursion', 'excursion_name', 'method', 'status', 'is_expired',
            'signed_name', 'response_notes', 'responded_at', 'expires_at', 'created_at',
        ]


class ConsentRequestCreateSerializer(serializers.Serializer):
    """
    Handles both digital and manual creation in one shape — manual
    submissions include the outcome directly, digital ones don't
    (outcome is set later, by the parent).
    """
    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all())
    guardian = serializers.PrimaryKeyRelatedField(queryset=Guardian.objects.all(), required=False, allow_null=True)
    consent_type = serializers.ChoiceField(choices=ConsentRequest.CONSENT_TYPE_CHOICES)
    excursion = serializers.PrimaryKeyRelatedField(queryset=Excursion.objects.all(), required=False, allow_null=True)
    method = serializers.ChoiceField(choices=ConsentRequest.METHOD_CHOICES)

    # Manual-only fields
    status = serializers.ChoiceField(choices=[('granted', 'Granted'), ('denied', 'Denied')], required=False)
    signed_name = serializers.CharField(required=False, allow_blank=True)
    response_notes = serializers.CharField(required=False, allow_blank=True)

    def validate_student(self, value):
        school = self.context.get('school')
        if school and value.school != school:
            raise serializers.ValidationError("Student does not belong to your school.")
        return value

    def validate_excursion(self, value):
        school = self.context.get('school')
        if value and school and value.school != school:
            raise serializers.ValidationError("Excursion does not belong to your school.")
        return value

    def validate(self, attrs):
        if attrs['consent_type'] == 'excursion' and not attrs.get('excursion'):
            raise serializers.ValidationError({'excursion': 'Required when consent_type is excursion.'})
        if attrs['method'] == 'manual' and not attrs.get('status'):
            raise serializers.ValidationError({'status': 'Required for manual consent records.'})
        return attrs


class ConsentRequestPublicSerializer(serializers.Serializer):
    """What the parent's page sees before responding."""
    school_name = serializers.CharField()
    student_name = serializers.CharField()
    consent_type = serializers.CharField()
    consent_type_display = serializers.CharField()
    excursion_name = serializers.CharField(allow_null=True)
    excursion_description = serializers.CharField(allow_null=True)
    excursion_date = serializers.DateField(allow_null=True)
    excursion_location = serializers.CharField(allow_null=True)

from apps.communications.models import Message
from apps.academics.models import ClassRoom
from apps.tenants.models import SchoolMember


class MessageSerializer(serializers.ModelSerializer):
    composed_by_name = serializers.CharField(source='composed_by.user.full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.user.full_name', read_only=True)
    audience_display = serializers.CharField(source='get_audience_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    target_student_name = serializers.CharField(source='target_student.full_name', read_only=True)
    target_staff_name = serializers.CharField(source='target_staff_member.user.full_name', read_only=True)
    target_classroom_name = serializers.CharField(source='target_classroom.full_name', read_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 'title', 'body', 'audience_type', 'audience_display',
            'target_student', 'target_student_name',
            'target_staff_member', 'target_staff_name',
            'target_classroom', 'target_classroom_name',
            'status', 'status_display',
            'composed_by', 'composed_by_name',
            'reviewed_by', 'reviewed_by_name', 'reviewed_at', 'decline_reason',
            'recipient_count', 'sent_at', 'created_at',
        ]


class MessageComposeSerializer(serializers.ModelSerializer):
    """
    Shape validation for composing a message. Target fields are scoped to
    the requesting school in __init__ — same pattern as
    SubjectAssignmentCreateSerializer — so a composer can't reference
    another tenant's student/staff/classroom by id.
    """

    class Meta:
        model = Message
        fields = [
            'title', 'body', 'audience_type',
            'target_student', 'target_staff_member', 'target_classroom',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        school = self.context.get('school')
        if school is not None:
            self.fields['target_student'].queryset = Student.objects.filter(school=school)
            self.fields['target_staff_member'].queryset = SchoolMember.objects.filter(
                school=school, is_active=True
            )
            self.fields['target_classroom'].queryset = ClassRoom.objects.filter(school=school)

    def validate(self, attrs):
        audience = attrs.get('audience_type')
        required_field = {
            'single_guardian': 'target_student',
            'single_staff': 'target_staff_member',
            'class_guardians': 'target_classroom',
        }.get(audience)

        if required_field and not attrs.get(required_field):
            raise serializers.ValidationError({
                required_field: f"Required for audience type '{audience}'."
            })
        return attrs