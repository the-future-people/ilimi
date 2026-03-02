from django.contrib import admin
from apps.students.models import (
    Student, Guardian, StudentGuardian,
    EmergencyContact, StudentClassHistory
)


class StudentGuardianInline(admin.TabularInline):
    model = StudentGuardian
    extra = 1


class EmergencyContactInline(admin.TabularInline):
    model = EmergencyContact
    extra = 1


class StudentClassHistoryInline(admin.TabularInline):
    model = StudentClassHistory
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = [
        'student_id', 'full_name', 'gender', 'current_class',
        'school', 'status', 'enrollment_date'
    ]
    list_filter = ['school', 'status', 'gender', 'boarding_status', 'religion']
    search_fields = [
        'first_name', 'last_name', 'middle_name',
        'student_id', 'nhis_number'
    ]
    readonly_fields = ['student_id', 'created_at', 'updated_at']
    inlines = [StudentGuardianInline, EmergencyContactInline, StudentClassHistoryInline]
    fieldsets = (
        ('Identity', {
            'fields': (
                'student_id', 'first_name', 'middle_name', 'last_name',
                'date_of_birth', 'gender', 'nationality',
                'place_of_birth', 'home_town', 'mother_tongue',
            )
        }),
        ('School', {
            'fields': (
                'school', 'branch', 'current_class',
                'enrollment_date', 'expected_graduation_year',
                'previous_school', 'status', 'withdrawal_reason',
            )
        }),
        ('Official Documents', {
            'fields': ('birth_certificate_number', 'nhis_number')
        }),
        ('Contact & Address', {
            'fields': ('residential_address', 'city', 'region')
        }),
        ('Religion', {
            'fields': ('religion',)
        }),
        ('Health', {
            'fields': (
                'blood_group', 'known_allergies', 'medical_notes',
                'disability_status', 'disability_description',
            )
        }),
        ('Boarding', {
            'fields': (
                'boarding_status', 'house_dormitory',
                'bus_route', 'locker_number',
            )
        }),
        ('Extra', {
            'fields': ('talents_skills', 'additional_notes', 'siblings')
        }),
        ('Biometrics', {
            'fields': ('photo', 'fingerprint_data')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 'relationship', 'phone',
        'whatsapp_number', 'is_fee_payer'
    ]
    search_fields = ['first_name', 'last_name', 'phone', 'email']
    list_filter = ['relationship', 'is_fee_payer', 'nationality']


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'relationship', 'phone', 'student', 'is_primary']
    search_fields = ['full_name', 'phone']
    list_filter = ['relationship', 'is_primary']


@admin.register(StudentClassHistory)
class StudentClassHistoryAdmin(admin.ModelAdmin):
    list_display = ['student', 'classroom', 'academic_year', 'is_current', 'promoted']
    list_filter = ['academic_year', 'is_current', 'promoted']
    search_fields = ['student__first_name', 'student__last_name']