from django.contrib import admin
from apps.fees.models import (
    FeeType,
    FeeStructure,
    StudentFee,
    Payment,
    InstallmentPlan,
    Installment,
)


@admin.register(FeeType)
class FeeTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'school', 'is_active']
    list_filter = ['school', 'is_active']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = [
        'fee_type', 'class_level', 'term', 'branch',
        'amount', 'is_mandatory', 'is_active',
    ]
    list_filter = ['school', 'branch', 'term', 'class_level', 'is_mandatory', 'is_active']
    search_fields = ['fee_type__name']
    readonly_fields = ['created_at', 'updated_at']


class InstallmentInline(admin.TabularInline):
    model = Installment
    extra = 0
    readonly_fields = ['created_at', 'updated_at']


@admin.register(InstallmentPlan)
class InstallmentPlanAdmin(admin.ModelAdmin):
    list_display = [
        'student_fee', 'number_of_installments',
        'status', 'total_amount', 'amount_per_installment',
    ]
    list_filter = ['status']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [InstallmentInline]


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ['receipt_number', 'created_at', 'updated_at']


@admin.register(StudentFee)
class StudentFeeAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'fee_structure', 'term', 'amount_charged',
        'amount_paid', 'balance', 'status', 'due_date',
    ]
    list_filter = ['school', 'status', 'term']
    search_fields = ['student__first_name', 'student__last_name', 'student__student_id']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'receipt_number', 'student_fee', 'amount',
        'payment_method', 'status', 'payment_date',
    ]
    list_filter = ['school', 'payment_method', 'status']
    search_fields = ['receipt_number', 'student_fee__student__first_name']
    readonly_fields = ['receipt_number', 'created_at', 'updated_at']