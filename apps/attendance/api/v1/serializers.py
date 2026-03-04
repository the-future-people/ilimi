from rest_framework import serializers
from django.utils import timezone

from apps.attendance.models import (
    StudentAttendance,
    StaffAttendance,
    AttendanceSettings,
    AuthorisedPickup,
    PickupIncident,
)
from apps.students.models import Student
from apps.teachers.models import StaffProfile
from apps.academics.models import Term


# ── Attendance Settings ────────────────────────────────────────────────────────

class AttendanceSettingsSerializer(serializers.ModelSerializer):
    late_cutoff_display = serializers.CharField(read_only=True)

    class Meta:
        model = AttendanceSettings
        fields = [
            'id', 'school', 'branch',
            'school_start_time', 'late_grace_minutes',
            'school_close_time', 'unclocked_out_alert_time',
            'allow_fingerprint_exit',
            'sms_on_checkin', 'sms_on_checkout',
            'sms_on_late_arrival', 'sms_on_absence',
            'absence_notify_time',
            'late_cutoff_display',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'school', 'created_at', 'updated_at']


# ── Authorised Pickup ──────────────────────────────────────────────────────────

class AuthorisedPickupSerializer(serializers.ModelSerializer):
    """Full read serializer."""
    full_name = serializers.CharField(read_only=True)
    relationship_display = serializers.CharField(
        source='get_relationship_display', read_only=True
    )
    student_name = serializers.CharField(
        source='student.full_name', read_only=True
    )

    class Meta:
        model = AuthorisedPickup
        fields = [
            'id', 'school', 'student', 'student_name',
            'first_name', 'last_name', 'full_name',
            'relationship', 'relationship_display',
            'phone', 'ghana_card_number', 'photo',
            'is_active', 'added_by', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'school', 'added_by', 'created_at', 'updated_at']


class AuthorisedPickupCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorisedPickup
        fields = [
            'student', 'first_name', 'last_name',
            'relationship', 'phone', 'ghana_card_number',
            'photo', 'is_active', 'notes',
        ]

    def validate_student(self, value):
        school = self.context.get('school')
        if value.school != school:
            raise serializers.ValidationError(
                "This student does not belong to your school."
            )
        return value

    def validate_phone(self, value):
        if not value:
            raise serializers.ValidationError("Phone number is required.")
        return value


# ── Pickup Incident ────────────────────────────────────────────────────────────

class PickupIncidentSerializer(serializers.ModelSerializer):
    """Full read serializer."""
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    student_name = serializers.CharField(
        source='student.full_name', read_only=True
    )
    guardian_name = serializers.CharField(
        source='guardian_notified.full_name', read_only=True
    )
    resolved_by_name = serializers.SerializerMethodField()
    is_resolved = serializers.BooleanField(read_only=True)

    class Meta:
        model = PickupIncident
        fields = [
            'id', 'school', 'student', 'student_name',
            'attempted_by_name', 'attempted_by_phone',
            'attempted_by_id_number', 'reason_given', 'attempted_at',
            'guardian_notified', 'guardian_name',
            'authorisation_sms_sent', 'authorisation_sms_sent_at',
            'guardian_response_at',
            'status', 'status_display', 'student_released',
            'resolved_by', 'resolved_by_name',
            'resolved_at', 'resolution_notes',
            'escalated', 'escalated_at',
            'is_resolved',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'school', 'attempted_at',
            'authorisation_sms_sent', 'authorisation_sms_sent_at',
            'created_at', 'updated_at',
        ]

    def get_resolved_by_name(self, obj):
        if obj.resolved_by:
            return obj.resolved_by.user.get_full_name()
        return None


class PickupIncidentCreateSerializer(serializers.ModelSerializer):
    """Used when staff logs a new incident at the gate."""

    class Meta:
        model = PickupIncident
        fields = [
            'student',
            'attempted_by_name', 'attempted_by_phone',
            'attempted_by_id_number', 'reason_given',
        ]

    def validate_student(self, value):
        school = self.context.get('school')
        if value.school != school:
            raise serializers.ValidationError(
                "This student does not belong to your school."
            )
        return value


class PickupIncidentResolveSerializer(serializers.ModelSerializer):
    """Used when staff resolves a pending incident."""

    class Meta:
        model = PickupIncident
        fields = [
            'status', 'student_released',
            'resolution_notes', 'guardian_response_at',
            'escalated',
        ]

    def validate(self, data):
        status = data.get('status')
        student_released = data.get('student_released', False)

        if status == 'authorised' and not student_released:
            raise serializers.ValidationError(
                "student_released must be True when status is authorised."
            )
        if status == 'denied' and student_released:
            raise serializers.ValidationError(
                "student_released must be False when status is denied."
            )
        if not data.get('resolution_notes'):
            raise serializers.ValidationError(
                "Resolution notes are required when resolving an incident."
            )
        return data


# ── Student Attendance ─────────────────────────────────────────────────────────

class StudentAttendanceSerializer(serializers.ModelSerializer):
    """Full read serializer."""
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    source_display = serializers.CharField(
        source='get_source_display', read_only=True
    )
    student_name = serializers.CharField(
        source='student.full_name', read_only=True
    )
    marked_by_name = serializers.SerializerMethodField()
    picked_up_by_name = serializers.CharField(
        source='picked_up_by.full_name', read_only=True
    )
    is_clocked_out = serializers.BooleanField(read_only=True)
    needs_pickup_alert = serializers.BooleanField(read_only=True)

    class Meta:
        model = StudentAttendance
        fields = [
            'id', 'school', 'branch', 'student', 'student_name',
            'term', 'marked_by', 'marked_by_name',
            'date', 'status', 'status_display',
            'source', 'source_display', 'locked',
            'clock_in_time', 'via_fingerprint',
            'clock_out_time', 'clock_out_via_fingerprint',
            'early_dismissal', 'early_dismissal_reason',
            'picked_up_by', 'picked_up_by_name', 'pickup_verified_by',
            'guardian_notified', 'notification_sent_at',
            'override_reason', 'override_by',
            'remarks',
            'is_clocked_out', 'needs_pickup_alert',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'school', 'source', 'locked',
            'via_fingerprint', 'clock_out_via_fingerprint',
            'guardian_notified', 'notification_sent_at',
            'override_by', 'created_at', 'updated_at',
        ]

    def get_marked_by_name(self, obj):
        if obj.marked_by:
            return obj.marked_by.user.get_full_name()
        return None


class StudentAttendanceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_clocked_out = serializers.BooleanField(read_only=True)

    class Meta:
        model = StudentAttendance
        fields = [
            'id', 'student', 'student_name', 'date',
            'status', 'status_display', 'source', 'locked',
            'clock_in_time', 'clock_out_time',
            'via_fingerprint', 'guardian_notified',
            'is_clocked_out',
        ]


class StudentAttendanceCreateSerializer(serializers.ModelSerializer):
    """Manual single-record creation."""

    class Meta:
        model = StudentAttendance
        fields = [
            'student', 'term', 'date', 'status',
            'clock_in_time', 'remarks', 'branch',
        ]

    def validate(self, data):
        school = self.context.get('school')
        student = data.get('student')
        term = data.get('term')
        date = data.get('date', timezone.localdate())

        # Tenant check
        if student and student.school != school:
            raise serializers.ValidationError(
                "This student does not belong to your school."
            )
        if term and term.school != school:
            raise serializers.ValidationError(
                "This term does not belong to your school."
            )

        # Duplicate check
        exists = StudentAttendance.objects.filter(
            student=student, date=date, term=term
        ).exists()
        if exists:
            raise serializers.ValidationError(
                f"An attendance record already exists for this student on {date}."
            )

        return data


class StudentAttendanceBulkItemSerializer(serializers.Serializer):
    """Single item within a bulk mark request."""
    student_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=['present', 'absent', 'late', 'excused'])
    clock_in_time = serializers.TimeField(required=False, allow_null=True)
    remarks = serializers.CharField(required=False, allow_blank=True, default='')


class StudentAttendanceBulkSerializer(serializers.Serializer):
    """Bulk mark attendance for a list of students."""
    term_id = serializers.IntegerField()
    date = serializers.DateField(required=False)
    records = StudentAttendanceBulkItemSerializer(many=True, min_length=1)

    def validate_term_id(self, value):
        school = self.context.get('school')
        try:
            term = Term.objects.get(pk=value, school=school)
        except Term.DoesNotExist:
            raise serializers.ValidationError(
                "Term not found or does not belong to your school."
            )
        return value


class StudentCheckoutSerializer(serializers.Serializer):
    """Clock out / pickup a student."""
    clock_out_time = serializers.TimeField(required=False, allow_null=True)
    picked_up_by_id = serializers.IntegerField(required=False, allow_null=True)
    pickup_verified_by_id = serializers.IntegerField(required=False, allow_null=True)
    early_dismissal_reason = serializers.CharField(required=False, allow_blank=True)

    def validate_picked_up_by_id(self, value):
        if value is None:
            return value
        school = self.context.get('school')
        try:
            pickup = AuthorisedPickup.objects.get(pk=value, school=school, is_active=True)
        except AuthorisedPickup.DoesNotExist:
            raise serializers.ValidationError(
                "Authorised pickup person not found or is inactive."
            )
        return value


class StudentAttendanceUpdateSerializer(serializers.ModelSerializer):
    """
    Update a student attendance record.
    If record is locked, override_reason is mandatory.
    """
    override_reason = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = StudentAttendance
        fields = [
            'status', 'clock_in_time', 'remarks',
            'early_dismissal', 'early_dismissal_reason',
            'override_reason',
        ]

    def validate(self, data):
        instance = self.instance
        if instance and instance.locked:
            if not data.get('override_reason'):
                raise serializers.ValidationError(
                    "This record was created by a fingerprint device and is locked. "
                    "An override_reason is required to make changes."
                )
        return data


# ── Staff Attendance ───────────────────────────────────────────────────────────

class StaffAttendanceSerializer(serializers.ModelSerializer):
    """Full read serializer."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    staff_name = serializers.CharField(source='staff.full_name', read_only=True)

    class Meta:
        model = StaffAttendance
        fields = [
            'id', 'school', 'branch', 'staff', 'staff_name',
            'term', 'date', 'status', 'status_display',
            'source', 'source_display', 'locked',
            'clock_in_time', 'clock_out_time',
            'via_fingerprint', 'hours_worked',
            'override_reason', 'remarks',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'school', 'source', 'locked',
            'via_fingerprint', 'hours_worked',
            'created_at', 'updated_at',
        ]


class StaffAttendanceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    staff_name = serializers.CharField(source='staff.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = StaffAttendance
        fields = [
            'id', 'staff', 'staff_name', 'date',
            'status', 'status_display', 'source', 'locked',
            'clock_in_time', 'clock_out_time', 'hours_worked',
            'via_fingerprint',
        ]


class StaffAttendanceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffAttendance
        fields = [
            'staff', 'term', 'date', 'status',
            'clock_in_time', 'clock_out_time',
            'remarks', 'branch',
        ]

    def validate(self, data):
        school = self.context.get('school')
        staff = data.get('staff')
        term = data.get('term')
        date = data.get('date', timezone.localdate())

        if staff and staff.school != school:
            raise serializers.ValidationError(
                "This staff member does not belong to your school."
            )
        if term and term.school != school:
            raise serializers.ValidationError(
                "This term does not belong to your school."
            )

        exists = StaffAttendance.objects.filter(
            staff=staff, date=date, term=term
        ).exists()
        if exists:
            raise serializers.ValidationError(
                f"An attendance record already exists for this staff member on {date}."
            )
        return data


class StaffAttendanceBulkItemSerializer(serializers.Serializer):
    staff_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=['present', 'absent', 'late', 'excused'])
    clock_in_time = serializers.TimeField(required=False, allow_null=True)
    clock_out_time = serializers.TimeField(required=False, allow_null=True)
    remarks = serializers.CharField(required=False, allow_blank=True, default='')


class StaffAttendanceBulkSerializer(serializers.Serializer):
    term_id = serializers.IntegerField()
    date = serializers.DateField(required=False)
    records = StaffAttendanceBulkItemSerializer(many=True, min_length=1)

    def validate_term_id(self, value):
        school = self.context.get('school')
        try:
            Term.objects.get(pk=value, school=school)
        except Term.DoesNotExist:
            raise serializers.ValidationError(
                "Term not found or does not belong to your school."
            )
        return value


class StaffAttendanceUpdateSerializer(serializers.ModelSerializer):
    override_reason = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = StaffAttendance
        fields = [
            'status', 'clock_in_time', 'clock_out_time',
            'remarks', 'override_reason',
        ]

    def validate(self, data):
        instance = self.instance
        if instance and instance.locked:
            if not data.get('override_reason'):
                raise serializers.ValidationError(
                    "This record was created by a fingerprint device and is locked. "
                    "An override_reason is required to make changes."
                )
        return data


# ── Device Ingest ──────────────────────────────────────────────────────────────

class DeviceIngestSerializer(serializers.Serializer):
    """
    Payload sent by the fingerprint hardware device.
    Device authenticates via API key, not JWT.
    """
    device_id = serializers.CharField(max_length=100)
    fingerprint_id = serializers.CharField(max_length=100)
    scanned_at = serializers.DateTimeField()
    scan_type = serializers.ChoiceField(choices=['entry', 'exit'])

    def validate_device_id(self, value):
        # TODO: validate device_id against a registered Device model
        # when hardware integration is fully implemented
        if not value:
            raise serializers.ValidationError("device_id is required.")
        return value