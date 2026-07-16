from rest_framework import serializers

from apps.students.models import (
    Student,
    Guardian,
    StudentGuardian,
    EmergencyContact,
    StudentClassHistory,
)


# ── Guardian Serializers ──────────────────────────────────────────────────

class GuardianSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guardian
        fields = [
            'id', 'first_name', 'last_name', 'relationship', 'occupation',
            'employer', 'nationality', 'phone', 'whatsapp_number', 'email',
            'residential_address', 'is_fee_payer',
        ]


class GuardianCreateSerializer(serializers.ModelSerializer):
    is_primary = serializers.BooleanField(default=False, write_only=True)
    occupation_name = serializers.CharField(
        required=False, allow_blank=True, write_only=True,
        help_text="Free-text occupation name; resolved to an Occupation record on save."
    )

    class Meta:
        model = Guardian
        fields = [
            'title', 'first_name', 'last_name', 'relationship',
            'occupation_name', 'employer', 'nationality',
            'phone', 'whatsapp_number', 'secondary_phone', 'email',
            'residential_address', 'digital_address',
            'ghana_card_number', 'ghana_card_front', 'ghana_card_back',
            'photo', 'fingerprint_data', 'can_pickup',
            'is_fee_payer', 'is_primary',
        ]


class StudentGuardianSerializer(serializers.ModelSerializer):
    guardian = GuardianSerializer(read_only=True)

    class Meta:
        model = StudentGuardian
        fields = ['id', 'guardian', 'is_primary']


# ── Emergency Contact Serializers ─────────────────────────────────────────

class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ['id', 'full_name', 'relationship', 'phone', 'whatsapp_number', 'is_primary']


class EmergencyContactCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ['full_name', 'relationship', 'phone', 'whatsapp_number', 'is_primary']


# ── Class History Serializer ──────────────────────────────────────────────

class StudentClassHistorySerializer(serializers.ModelSerializer):
    classroom_name = serializers.CharField(source='classroom.full_name', read_only=True)
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)

    class Meta:
        model = StudentClassHistory
        fields = [
            'id', 'classroom', 'classroom_name',
            'academic_year', 'academic_year_name',
            'is_current', 'promoted', 'remarks',
        ]


# ── Student Serializers ───────────────────────────────────────────────────

class StudentSerializer(serializers.ModelSerializer):
    """Full read serializer — used for detail view."""
    full_name = serializers.SerializerMethodField()
    enrollment_date = serializers.DateField()
    classroom_name = serializers.CharField(source='current_class.full_name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    guardians = StudentGuardianSerializer(
    source='student_guardians', many=True, read_only=True
)
    emergency_contacts = EmergencyContactSerializer(many=True, read_only=True)

    class Meta:
        model = Student
        fields = [
            'id', 'student_id', 'full_name',
            'first_name', 'middle_name', 'last_name',
            'date_of_birth', 'gender', 'place_of_birth', 'home_town',
            'nationality', 'mother_tongue', 'birth_certificate_number',
            'nhis_number', 'residential_address', 'city', 'region',
            'religion', 'blood_group', 'known_allergies', 'medical_notes',
            'disability_status', 'disability_description',
            'enrollment_date', 'expected_graduation_year', 'previous_school',
            'status', 'withdrawal_reason', 'boarding_status',
            'house_dormitory', 'bus_route', 'locker_number',
            'talents_skills', 'additional_notes',
            'photo', 'current_class', 'classroom_name', 'branch', 'branch_name',
            'guardians', 'emergency_contacts',
        ]

    def get_full_name(self, obj):
        return obj.full_name


class StudentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    full_name = serializers.SerializerMethodField()
    enrollment_date = serializers.DateField()
    classroom_name = serializers.CharField(source='current_class.full_name', read_only=True)
    current_class_id = serializers.IntegerField(source='current_class.id', read_only=True)
    class_level_order = serializers.IntegerField(source='current_class.class_level.order', read_only=True)
    primary_guardian_name = serializers.SerializerMethodField()
    primary_guardian_phone = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'id', 'student_id', 'full_name',
            'gender', 'status', 'classroom_name', 'current_class_id',
            'class_level_order', 'enrollment_date', 'photo',
            'primary_guardian_name', 'primary_guardian_phone',
        ]

    def get_full_name(self, obj):
        return obj.full_name

    def _get_primary_link(self, obj):
        links = list(obj.student_guardians.all())
        return links[0] if links else None

    def get_primary_guardian_name(self, obj):
        link = self._get_primary_link(obj)
        return link.guardian.full_name if link else None

    def get_primary_guardian_phone(self, obj):
        link = self._get_primary_link(obj)
        return link.guardian.phone if link else None


class StudentEnrolSerializer(serializers.ModelSerializer):
    """Write serializer for enrolment — nested guardians + emergency contacts."""
    enrollment_date = serializers.DateField(required=False)
    guardians = GuardianCreateSerializer(many=True, write_only=True)
    emergency_contacts = EmergencyContactCreateSerializer(
        many=True, write_only=True, required=False, default=[]
    )

    sibling_ids = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(), many=True, write_only=True,
        required=False, default=list,
        help_text="IDs of existing students to link as siblings."
    )

    class Meta:
        model = Student
        fields = [
            'first_name', 'middle_name', 'last_name',
            'date_of_birth', 'gender', 'place_of_birth', 'home_town',
            'nationality', 'mother_tongue', 'ghana_card_number',
            'birth_certificate_number',
            'nhis_number', 'residential_address', 'city', 'region',
            'religion', 'blood_group', 'known_allergies', 'medical_notes',
            'disability_status', 'disability_description',
            'enrollment_date', 'expected_graduation_year', 'previous_school',
            'boarding_status', 'house_dormitory', 'bus_route',
            'locker_number', 'talents_skills', 'additional_notes',
            'photo', 'fingerprint_data', 'current_class',
            'guardians', 'emergency_contacts', 'sibling_ids',
        ]

    def validate_guardians(self, value):
        if not value:
            raise serializers.ValidationError("At least one guardian is required.")
        primary_count = sum(1 for g in value if g.get('is_primary'))
        if primary_count == 0:
            value[0]['is_primary'] = True
        elif primary_count > 1:
            raise serializers.ValidationError(
                "Only one guardian can be marked as primary."
            )
        return value

    def validate_current_class(self, value):
        if value is None:
            return value
        school = self.context.get('school')
        if school and value.school != school:
            raise serializers.ValidationError(
                "Classroom does not belong to your school."
            )
        return value
    
    def validate_sibling_ids(self, value):
        school = self.context.get('school')
        if school:
            for student in value:
                if student.school != school:
                    raise serializers.ValidationError(
                        f"Student '{student.full_name}' does not belong to your school."
                    )
        return value


class StudentUpdateSerializer(serializers.ModelSerializer):
    """Partial update — protects system-managed and tenant fields."""
    enrollment_date = serializers.DateField(required=False)

    class Meta:
        model = Student
        exclude = ['school', 'branch', 'student_id', 'fingerprint_data']