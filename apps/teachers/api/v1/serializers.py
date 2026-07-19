from rest_framework import serializers

from apps.teachers.models import StaffProfile, StaffEmergencyContact


# ── Emergency Contact Serializers ───────────────────────────────────────────

class StaffEmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffEmergencyContact
        fields = ['id', 'full_name', 'relationship', 'phone', 'whatsapp_number', 'is_primary']


class StaffEmergencyContactCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffEmergencyContact
        fields = ['full_name', 'relationship', 'phone', 'whatsapp_number', 'is_primary']


# ── Staff Serializers ─────────────────────────────────────────────────────

class StaffProfileSerializer(serializers.ModelSerializer):
    """Full read serializer."""
    full_name = serializers.SerializerMethodField()
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    leave_days_remaining = serializers.IntegerField(read_only=True)
    subject_specializations_display = serializers.SerializerMethodField()
    position_name = serializers.CharField(source='position.name', read_only=True)
    emergency_contacts = StaffEmergencyContactSerializer(many=True, read_only=True)

    class Meta:
        model = StaffProfile
        fields = [
            'id', 'staff_id', 'full_name', 'title',
            'first_name', 'middle_name', 'last_name',
            'date_of_birth', 'gender', 'nationality',
            'marital_status', 'number_of_dependants', 'photo',
            'fingerprint_data', 'blood_group',
            'phone', 'whatsapp_number', 'secondary_phone', 'email',
            'residential_address', 'digital_address', 'city', 'region',
            'ghana_card_number', 'ghana_card_front', 'ghana_card_back',
            'ssnit_number', 'ntc_license_number',
            'highest_qualification', 'institution_attended', 'years_of_experience',
            'subject_specializations', 'subject_specializations_display',
            'employment_type', 'time_commitment', 'staff_category',
            'position', 'position_name', 'salary_grade',
            'date_of_first_appointment', 'date_joined_school',
            'is_on_probation', 'probation_end_date',
            'status', 'termination_date', 'termination_reason',
            'is_head_of_department',
            'leave_entitlement_days', 'leave_days_taken', 'leave_days_remaining',
            'bank_name', 'bank_branch', 'bank_account_number', 'momo_number',
            'next_of_kin_name', 'next_of_kin_relationship',
            'next_of_kin_phone', 'next_of_kin_address',
            'emergency_contacts',
            'branch', 'branch_name',
        ]

    def get_full_name(self, obj):
        return obj.full_name

    def get_subject_specializations_display(self, obj):
        return [
            {'id': s.id, 'name': s.name}
            for s in obj.subject_specializations.all()
        ]


class StaffProfileListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    full_name = serializers.SerializerMethodField()
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    position_name = serializers.CharField(source='position.name', read_only=True)
    badges = serializers.SerializerMethodField()

    class Meta:
        model = StaffProfile
        fields = [
            'id', 'staff_id', 'full_name', 'title', 'gender',
            'phone', 'email', 'employment_type', 'time_commitment', 'staff_category',
            'position_name', 'status', 'badges',
            'branch_name', 'date_joined_school', 'photo',
        ]

    def get_full_name(self, obj):
        return obj.full_name

    def get_badges(self, obj):
        types_present = {r.record_type for r in obj.records.all()}
        return [t for t in ('award', 'commendation') if t in types_present]


class StaffProfileCreateSerializer(serializers.ModelSerializer):
    """Write serializer for creating a new staff member."""
    position_name = serializers.CharField(
        required=False, allow_blank=True, write_only=True,
        help_text="Free-text position/role name; resolved to a Position record on save."
    )
    emergency_contacts = StaffEmergencyContactCreateSerializer(
        many=True, write_only=True, required=False, default=list
    )

    class Meta:
        model = StaffProfile
        fields = [
            'title', 'first_name', 'middle_name', 'last_name',
            'date_of_birth', 'gender', 'nationality',
            'marital_status', 'number_of_dependants', 'photo',
            'fingerprint_data', 'blood_group',
            'phone', 'whatsapp_number', 'secondary_phone', 'email',
            'residential_address', 'digital_address', 'city', 'region',
            'ghana_card_number', 'ghana_card_front', 'ghana_card_back',
            'ssnit_number', 'ntc_license_number',
            'highest_qualification', 'institution_attended', 'years_of_experience',
            'subject_specializations',
            'employment_type', 'time_commitment', 'staff_category',
            'position_name', 'salary_grade',
            'date_of_first_appointment', 'date_joined_school',
            'is_on_probation', 'probation_end_date',
            'is_head_of_department',
            'leave_entitlement_days',
            'bank_name', 'bank_branch', 'bank_account_number', 'momo_number',
            'next_of_kin_name', 'next_of_kin_relationship',
            'next_of_kin_phone', 'next_of_kin_address',
            'emergency_contacts',
            'branch',
        ]

    def validate_ghana_card_number(self, value):
        if not value:
            return value
        school = self.context.get('school')
        qs = StaffProfile.objects.filter(
            school=school, ghana_card_number=value
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A staff member with this Ghana Card number already exists."
            )
        return value

    def validate_ssnit_number(self, value):
        if not value:
            return value
        school = self.context.get('school')
        qs = StaffProfile.objects.filter(
            school=school, ssnit_number=value
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A staff member with this SSNIT number already exists."
            )
        return value

    def validate_phone(self, value):
        school = self.context.get('school')
        qs = StaffProfile.objects.filter(school=school, phone=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A staff member with this phone number already exists."
            )
        return value


class StaffProfileUpdateSerializer(serializers.ModelSerializer):
    """Partial update — protects system-managed and tenant fields."""

    class Meta:
        model = StaffProfile
        exclude = ['school', 'branch', 'staff_id', 'user']