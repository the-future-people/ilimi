from django.contrib import admin
from apps.attendance.models import AttendanceSettings
from django.utils.html import format_html
from django.utils import timezone
from apps.attendance.models import (
    StudentAttendance,
    StaffAttendance,
    AttendanceSettings,
    AuthorisedPickup,
    PickupIncident,
)


# ── Attendance Settings ────────────────────────────────────────────────────────

@admin.register(AttendanceSettings)
class AttendanceSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'school', 'branch', 'school_start_time', 'late_grace_minutes',
        'school_close_time', 'sms_on_checkin', 'sms_on_absence',
    ]
    list_filter = ['school', 'sms_on_checkin', 'sms_on_absence']
    search_fields = ['school__name', 'branch__name']

    fieldsets = (
        ('Scope', {
            'fields': ('school', 'branch'),
            'description': 'Leave branch blank for school-wide settings.'
        }),
        ('Timing', {
            'fields': (
                'school_start_time', 'late_grace_minutes',
                'school_close_time', 'unclocked_out_alert_time',
            )
        }),
        ('Fingerprint', {
            'fields': ('allow_fingerprint_exit',)
        }),
        ('SMS Triggers', {
            'fields': (
                'sms_on_checkin', 'sms_on_checkout',
                'sms_on_late_arrival', 'sms_on_absence',
                'absence_notify_time',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ['created_at', 'updated_at']


# ── Authorised Pickup ──────────────────────────────────────────────────────────

@admin.register(AuthorisedPickup)
class AuthorisedPickupAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 'student', 'relationship_display',
        'phone', 'ghana_card_number', 'is_active', 'added_by',
    ]
    list_filter = ['is_active', 'relationship', 'school']
    search_fields = [
        'first_name', 'last_name', 'phone', 'ghana_card_number',
        'student__first_name', 'student__last_name',
    ]
    readonly_fields = ['created_at', 'updated_at', 'photo_preview']

    fieldsets = (
        ('Scope', {
            'fields': ('school', 'student')
        }),
        ('Personal Details', {
            'fields': (
                'first_name', 'last_name', 'relationship',
                'phone', 'ghana_card_number',
                'photo', 'photo_preview',
            )
        }),
        ('Status', {
            'fields': ('is_active', 'added_by', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Name'

    def relationship_display(self, obj):
        return obj.get_relationship_display()
    relationship_display.short_description = 'Relationship'

    def photo_preview(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="height:80px; border-radius:4px;" />',
                obj.photo.url
            )
        return 'No photo uploaded'
    photo_preview.short_description = 'Photo Preview'


# ── Pickup Incident ────────────────────────────────────────────────────────────

@admin.register(PickupIncident)
class PickupIncidentAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'attempted_by_name', 'attempted_at',
        'status_badge', 'student_released', 'escalated', 'resolved_by',
    ]
    list_filter = ['status', 'student_released', 'escalated', 'school']
    search_fields = [
        'student__first_name', 'student__last_name',
        'attempted_by_name', 'attempted_by_phone',
    ]
    readonly_fields = [
        'attempted_at', 'authorisation_sms_sent_at',
        'created_at', 'updated_at',
    ]
    date_hierarchy = 'attempted_at'

    fieldsets = (
        ('Scope', {
            'fields': ('school', 'student')
        }),
        ('Person Who Arrived', {
            'fields': (
                'attempted_by_name', 'attempted_by_phone',
                'attempted_by_id_number', 'reason_given', 'attempted_at',
            )
        }),
        ('Guardian Authorisation', {
            'fields': (
                'guardian_notified', 'authorisation_sms_sent',
                'authorisation_sms_sent_at', 'guardian_response_at',
            )
        }),
        ('Resolution', {
            'fields': (
                'status', 'student_released',
                'resolved_by', 'resolved_at', 'resolution_notes',
            )
        }),
        ('Escalation', {
            'fields': ('escalated', 'escalated_at'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def status_badge(self, obj):
        colours = {
            'pending':   '#f59e0b',
            'authorised': '#10b981',
            'denied':    '#ef4444',
            'escalated': '#6366f1',
        }
        colour = colours.get(obj.status, '#6b7280')
        return format_html(
            '<span style="'
            'background:{}; color:#fff; padding:2px 10px; '
            'border-radius:12px; font-size:11px; font-weight:600;">'
            '{}</span>',
            colour, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


# ── Student Attendance ─────────────────────────────────────────────────────────

@admin.register(StudentAttendance)
class StudentAttendanceAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'date', 'status_badge', 'source',
        'clock_in_time', 'clock_out_time', 'term',
        'via_fingerprint', 'guardian_notified', 'marked_by',
    ]
    list_filter = [
        'status', 'source', 'locked', 'term', 'branch',
        'via_fingerprint', 'guardian_notified', 'early_dismissal',
    ]
    search_fields = [
        'student__first_name', 'student__last_name', 'student__student_id'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'notification_sent_at',
        'locked', 'source',
    ]
    date_hierarchy = 'date'

    fieldsets = (
        ('Linkage', {
            'fields': ('school', 'branch', 'student', 'term', 'marked_by')
        }),
        ('Attendance', {
            'fields': (
                'date', 'status', 'source', 'locked',
                'clock_in_time', 'via_fingerprint', 'remarks',
            )
        }),
        ('Clock Out / Pickup', {
            'fields': (
                'clock_out_time', 'clock_out_via_fingerprint',
                'early_dismissal', 'early_dismissal_reason',
                'picked_up_by', 'pickup_verified_by',
            )
        }),
        ('Guardian Notification', {
            'fields': ('guardian_notified', 'notification_sent_at')
        }),
        ('Override Audit', {
            'fields': ('override_reason', 'override_by'),
            'classes': ('collapse',),
            'description': (
                'Only populated when an admin overrides a locked fingerprint record.'
            ),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def status_badge(self, obj):
        colours = {
            'present': '#10b981',
            'absent':  '#ef4444',
            'late':    '#f59e0b',
            'excused': '#6366f1',
        }
        colour = colours.get(obj.status, '#6b7280')
        return format_html(
            '<span style="'
            'background:{}; color:#fff; padding:2px 10px; '
            'border-radius:12px; font-size:11px; font-weight:600;">'
            '{}</span>',
            colour, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def get_readonly_fields(self, request, obj=None):
        """
        If the record is locked (fingerprint-sourced), make all fields
        readonly for non-superusers. Superusers can still edit but must
        provide an override_reason.
        """
        readonly = list(self.readonly_fields)
        if obj and obj.locked and not request.user.is_superuser:
            readonly += [
                'date', 'status', 'clock_in_time', 'via_fingerprint',
                'clock_out_time', 'clock_out_via_fingerprint',
                'student', 'term', 'branch',
            ]
        return readonly

    def save_model(self, request, obj, form, change):
        """
        Auto-populate override_by when a superuser edits a locked record.
        """
        if change and obj.locked and request.user.is_superuser:
            member = request.user.schoolmember_set.filter(is_active=True).first()
            if member:
                obj.override_by = member
        super().save_model(request, obj, form, change)


# ── Staff Attendance ───────────────────────────────────────────────────────────

@admin.register(StaffAttendance)
class StaffAttendanceAdmin(admin.ModelAdmin):
    list_display = [
        'staff', 'date', 'status_badge', 'source',
        'clock_in_time', 'clock_out_time', 'hours_worked', 'term',
        'via_fingerprint',
    ]
    list_filter = ['status', 'source', 'locked', 'term', 'branch', 'via_fingerprint']
    search_fields = ['staff__first_name', 'staff__last_name', 'staff__staff_id']
    readonly_fields = ['created_at', 'updated_at', 'hours_worked', 'locked', 'source']
    date_hierarchy = 'date'

    fieldsets = (
        ('Linkage', {
            'fields': ('school', 'branch', 'staff', 'term')
        }),
        ('Attendance', {
            'fields': (
                'date', 'status', 'source', 'locked',
                'clock_in_time', 'clock_out_time',
                'via_fingerprint', 'hours_worked', 'remarks',
            )
        }),
        ('Override Audit', {
            'fields': ('override_reason',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def status_badge(self, obj):
        colours = {
            'present': '#10b981',
            'absent':  '#ef4444',
            'late':    '#f59e0b',
            'excused': '#6366f1',
        }
        colour = colours.get(obj.status, '#6b7280')
        return format_html(
            '<span style="'
            'background:{}; color:#fff; padding:2px 10px; '
            'border-radius:12px; font-size:11px; font-weight:600;">'
            '{}</span>',
            colour, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj and obj.locked and not request.user.is_superuser:
            readonly += [
                'date', 'status', 'clock_in_time',
                'clock_out_time', 'via_fingerprint',
                'staff', 'term', 'branch',
            ]
        return readonly