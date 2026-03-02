from django.contrib import admin
from apps.teachers.models import StaffProfile


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = [
        'staff_id', 'full_name', 'gender', 'employment_type',
        'status', 'phone', 'branch', 'date_joined_school',
    ]
    list_filter = ['status', 'employment_type', 'gender', 'branch', 'school']
    search_fields = ['first_name', 'last_name', 'staff_id', 'phone', 'ghana_card_number']
    readonly_fields = ['staff_id', 'created_at', 'updated_at']

    fieldsets = (
        ('School Linkage', {
            'fields': ('school', 'branch', 'user')
        }),
        ('Identity', {
            'fields': (
                'staff_id', 'first_name', 'middle_name', 'last_name',
                'date_of_birth', 'gender', 'nationality',
                'marital_status', 'number_of_dependants', 'photo',
            )
        }),
        ('Contact', {
            'fields': (
                'phone', 'whatsapp_number', 'email',
                'residential_address', 'city', 'region',
            )
        }),
        ('Official Documents', {
            'fields': (
                'ghana_card_number', 'ssnit_number', 'ntc_license_number',
            )
        }),
        ('Qualifications & Experience', {
            'fields': (
                'highest_qualification', 'institution_attended',
                'years_of_experience', 'subject_specializations',
            )
        }),
        ('Employment', {
            'fields': (
                'employment_type', 'salary_grade',
                'date_of_first_appointment', 'date_joined_school',
                'is_on_probation', 'probation_end_date',
                'status', 'termination_date', 'termination_reason',
                'is_head_of_department',
            )
        }),
        ('Leave', {
            'fields': ('leave_entitlement_days', 'leave_days_taken')
        }),
        ('Banking', {
            'fields': (
                'bank_name', 'bank_branch',
                'bank_account_number', 'momo_number',
            )
        }),
        ('Next of Kin', {
            'fields': (
                'next_of_kin_name', 'next_of_kin_relationship',
                'next_of_kin_phone', 'next_of_kin_address',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )