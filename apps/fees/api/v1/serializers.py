from rest_framework import serializers
from apps.fees.models import (
    FeeType,
    FeeStructure,
    StudentFee,
    Payment,
    InstallmentPlan,
    Installment,
)


# ── Fee Type Serializers ──────────────────────────────────────────────────

class FeeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeType
        fields = ['id', 'name', 'description', 'is_active']


class FeeTypeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeType
        fields = ['name', 'description', 'is_active']

    def validate_name(self, value):
        school = self.context.get('school')
        qs = FeeType.objects.filter(school=school, name=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                f"A fee type named '{value}' already exists for this school."
            )
        return value


# ── Fee Structure Serializers ─────────────────────────────────────────────

class FeeStructureSerializer(serializers.ModelSerializer):
    fee_type_name = serializers.CharField(source='fee_type.name', read_only=True)
    class_level_name = serializers.CharField(source='class_level.display_name', read_only=True)
    term_name = serializers.CharField(source='term.get_name_display', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = FeeStructure
        fields = [
            'id', 'fee_type', 'fee_type_name',
            'class_level', 'class_level_name',
            'term', 'term_name',
            'branch', 'branch_name',
            'amount', 'is_mandatory', 'is_active',
        ]


class FeeStructureCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeStructure
        fields = [
            'fee_type', 'class_level', 'term',
            'branch', 'amount', 'is_mandatory', 'is_active',
        ]

    def validate(self, attrs):
        school = self.context.get('school')
        qs = FeeStructure.objects.filter(
            school=school,
            branch=attrs.get('branch'),
            fee_type=attrs.get('fee_type'),
            class_level=attrs.get('class_level'),
            term=attrs.get('term'),
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A fee structure for this fee type, class level, term, and branch already exists."
            )
        return attrs


# ── Student Fee Serializers ───────────────────────────────────────────────

class StudentFeeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    fee_type_name = serializers.CharField(
        source='fee_structure.fee_type.name', read_only=True
    )
    term_name = serializers.CharField(source='term.get_name_display', read_only=True)
    balance = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = StudentFee
        fields = [
            'id', 'student', 'student_name', 'student_id',
            'fee_structure', 'fee_type_name',
            'term', 'term_name',
            'amount_charged', 'amount_paid', 'discount',
            'balance', 'status', 'due_date',
            'waiver_reason', 'notes',
        ]


class StudentFeeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentFee
        fields = [
            'student', 'fee_structure', 'term',
            'amount_charged', 'discount', 'due_date',
            'waiver_reason', 'notes',
        ]

    def validate(self, attrs):
        qs = StudentFee.objects.filter(
            student=attrs.get('student'),
            fee_structure=attrs.get('fee_structure'),
            term=attrs.get('term'),
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "This fee has already been assigned to this student for this term."
            )
        return attrs


class StudentFeeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentFee
        fields = [
            'amount_charged', 'discount', 'due_date',
            'status', 'waiver_reason', 'notes',
        ]


# ── Payment Serializers ───────────────────────────────────────────────────

class PaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(
        source='student_fee.student.full_name', read_only=True
    )
    fee_type_name = serializers.CharField(
        source='student_fee.fee_structure.fee_type.name', read_only=True
    )

    class Meta:
        model = Payment
        fields = [
            'id', 'receipt_number', 'student_fee',
            'student_name', 'fee_type_name',
            'amount', 'payment_method', 'status',
            'received_by',
            'momo_provider', 'momo_number', 'momo_transaction_id',
            'bank_name', 'bank_reference',
            'paystack_reference', 'paystack_transaction_id',
            'payment_date', 'notes',
        ]


class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'student_fee', 'amount', 'payment_method',
            'received_by',
            'momo_provider', 'momo_number', 'momo_transaction_id',
            'bank_name', 'bank_reference',
            'payment_date', 'notes',
        ]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than zero.")
        return value

    def validate(self, attrs):
        student_fee = attrs.get('student_fee')
        amount = attrs.get('amount')
        if student_fee and amount:
            if amount > student_fee.balance:
                raise serializers.ValidationError(
                    f"Payment amount GHS {amount} exceeds outstanding balance of GHS {student_fee.balance}."
                )
        return attrs


# ── Installment Serializers ───────────────────────────────────────────────

class InstallmentSerializer(serializers.ModelSerializer):
    balance = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = Installment
        fields = [
            'id', 'installment_number', 'amount_due',
            'amount_paid', 'balance', 'due_date',
            'paid_date', 'status', 'notes',
        ]


class InstallmentPlanSerializer(serializers.ModelSerializer):
    installments = InstallmentSerializer(many=True, read_only=True)
    total_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    amount_per_installment = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    student_name = serializers.CharField(
        source='student_fee.student.full_name', read_only=True
    )

    class Meta:
        model = InstallmentPlan
        fields = [
            'id', 'student_fee', 'student_name',
            'number_of_installments', 'status',
            'total_amount', 'amount_per_installment',
            'installments', 'notes',
        ]


class InstallmentPlanCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstallmentPlan
        fields = ['student_fee', 'number_of_installments', 'notes']

    def validate_student_fee(self, value):
        if hasattr(value, 'installment_plan'):
            raise serializers.ValidationError(
                "An installment plan already exists for this student fee."
            )
        if value.status in ['paid', 'waived']:
            raise serializers.ValidationError(
                "Cannot create an installment plan for a fee that is already paid or waived."
            )
        return value

    def validate_number_of_installments(self, value):
        if value < 2:
            raise serializers.ValidationError(
                "An installment plan must have at least 2 installments."
            )
        return value