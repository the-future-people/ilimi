from decimal import Decimal
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import extend_schema

from apps.core.renderers import IlimiAPIRenderer
from apps.tenants.models import SchoolMember
from apps.fees.models import (
    FeeType,
    FeeStructure,
    StudentFee,
    Payment,
    InstallmentPlan,
    Installment,
)
from .serializers import (
    FeeTypeSerializer,
    FeeTypeCreateSerializer,
    FeeStructureSerializer,
    FeeStructureCreateSerializer,
    StudentFeeSerializer,
    StudentFeeCreateSerializer,
    StudentFeeUpdateSerializer,
    PaymentSerializer,
    PaymentCreateSerializer,
    InstallmentPlanSerializer,
    InstallmentPlanCreateSerializer,
)


# ── Mixin ─────────────────────────────────────────────────────────────────

class SchoolScopedMixin:
    def get_school(self):
        member = SchoolMember.objects.filter(
            user=self.request.user, is_active=True
        ).select_related('school').first()
        if not member:
            raise NotFound("No school found for your account.")
        return member.school

    def get_member(self):
        member = SchoolMember.objects.filter(
            user=self.request.user, is_active=True
        ).select_related('school', 'branch').first()
        if not member:
            raise NotFound("No school found for your account.")
        return member


# ── Fee Types ─────────────────────────────────────────────────────────────

@extend_schema(tags=["Fees"])
class FeeTypeListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = FeeTypeSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        fee_types = FeeType.objects.filter(school=school, is_active=True)
        serializer = FeeTypeSerializer(fee_types, many=True)
        return Response({'fee_types': serializer.data, 'count': fee_types.count()})

    def post(self, request, *args, **kwargs):
        school = self.get_school()
        serializer = FeeTypeCreateSerializer(
            data=request.data, context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        fee_type = serializer.save(school=school)
        return Response(
            {
                'message': f"Fee type '{fee_type.name}' created successfully.",
                **FeeTypeSerializer(fee_type).data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Fees"])
class FeeTypeDetailView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = FeeTypeSerializer

    def get_object(self, school, pk):
        try:
            return FeeType.objects.get(school=school, pk=pk)
        except FeeType.DoesNotExist:
            raise NotFound("Fee type not found.")

    def get(self, request, pk, *args, **kwargs):
        school = self.get_school()
        fee_type = self.get_object(school, pk)
        return Response(FeeTypeSerializer(fee_type).data)

    def patch(self, request, pk, *args, **kwargs):
        school = self.get_school()
        fee_type = self.get_object(school, pk)
        serializer = FeeTypeCreateSerializer(
            fee_type, data=request.data, partial=True,
            context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'Fee type updated successfully.',
            **FeeTypeSerializer(fee_type).data,
        })


# ── Fee Structures ────────────────────────────────────────────────────────

@extend_schema(tags=["Fees"])
class FeeStructureListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = FeeStructureSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        qs = FeeStructure.objects.filter(school=school).select_related(
            'fee_type', 'class_level', 'term', 'branch'
        )

        term_id = request.query_params.get('term')
        class_level_id = request.query_params.get('class_level')
        branch_id = request.query_params.get('branch')

        if term_id:
            qs = qs.filter(term_id=term_id)
        if class_level_id:
            qs = qs.filter(class_level_id=class_level_id)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)

        serializer = FeeStructureSerializer(qs, many=True)
        return Response({'fee_structures': serializer.data, 'count': qs.count()})

    def post(self, request, *args, **kwargs):
        school = self.get_school()
        serializer = FeeStructureCreateSerializer(
            data=request.data, context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        structure = serializer.save(school=school)
        return Response(
            {
                'message': f"Fee structure created successfully.",
                **FeeStructureSerializer(structure).data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Fees"])
class FeeStructureDetailView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = FeeStructureSerializer

    def get_object(self, school, pk):
        try:
            return FeeStructure.objects.get(school=school, pk=pk)
        except FeeStructure.DoesNotExist:
            raise NotFound("Fee structure not found.")

    def get(self, request, pk, *args, **kwargs):
        school = self.get_school()
        structure = self.get_object(school, pk)
        return Response(FeeStructureSerializer(structure).data)

    def patch(self, request, pk, *args, **kwargs):
        school = self.get_school()
        structure = self.get_object(school, pk)
        serializer = FeeStructureCreateSerializer(
            structure, data=request.data, partial=True,
            context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'Fee structure updated successfully.',
            **FeeStructureSerializer(structure).data,
        })


# ── Student Fees ──────────────────────────────────────────────────────────

@extend_schema(tags=["Fees"])
class StudentFeeListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = StudentFeeSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        qs = StudentFee.objects.filter(school=school).select_related(
            'student', 'fee_structure__fee_type', 'term'
        )

        student_id = request.query_params.get('student')
        term_id = request.query_params.get('term')
        status_filter = request.query_params.get('status')
        class_level_id = request.query_params.get('class_level')

        if student_id:
            qs = qs.filter(student_id=student_id)
        if term_id:
            qs = qs.filter(term_id=term_id)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if class_level_id:
            qs = qs.filter(
                student__current_class__class_level_id=class_level_id
            )

        serializer = StudentFeeSerializer(qs, many=True)
        return Response({'student_fees': serializer.data, 'count': qs.count()})

    def post(self, request, *args, **kwargs):
        school = self.get_school()
        serializer = StudentFeeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student_fee = serializer.save(school=school)
        return Response(
            {
                'message': 'Student fee assigned successfully.',
                **StudentFeeSerializer(student_fee).data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Fees"])
class StudentFeeDetailView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = StudentFeeSerializer

    def get_object(self, school, pk):
        try:
            return StudentFee.objects.get(school=school, pk=pk)
        except StudentFee.DoesNotExist:
            raise NotFound("Student fee not found.")

    def get(self, request, pk, *args, **kwargs):
        school = self.get_school()
        student_fee = self.get_object(school, pk)
        return Response(StudentFeeSerializer(student_fee).data)

    def patch(self, request, pk, *args, **kwargs):
        school = self.get_school()
        student_fee = self.get_object(school, pk)
        serializer = StudentFeeUpdateSerializer(
            student_fee, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        student_fee.update_status()
        return Response({
            'message': 'Student fee updated successfully.',
            **StudentFeeSerializer(student_fee).data,
        })


# ── Payments ──────────────────────────────────────────────────────────────

@extend_schema(tags=["Fees"])
class PaymentListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = PaymentSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        qs = Payment.objects.filter(school=school).select_related(
            'student_fee__student', 'student_fee__fee_structure__fee_type'
        )

        student_id = request.query_params.get('student')
        payment_method = request.query_params.get('payment_method')
        status_filter = request.query_params.get('status')

        if student_id:
            qs = qs.filter(student_fee__student_id=student_id)
        if payment_method:
            qs = qs.filter(payment_method=payment_method)
        if status_filter:
            qs = qs.filter(status=status_filter)

        serializer = PaymentSerializer(qs, many=True)
        return Response({'payments': serializer.data, 'count': qs.count()})

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        school = self.get_school()
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save(
            school=school,
            status='successful',
        )
        return Response(
            {
                'message': f"Payment of GHS {payment.amount} recorded successfully. Receipt: {payment.receipt_number}",
                **PaymentSerializer(payment).data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Fees"])
class PaymentDetailView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = PaymentSerializer

    def get_object(self, school, pk):
        try:
            return Payment.objects.get(school=school, pk=pk)
        except Payment.DoesNotExist:
            raise NotFound("Payment not found.")

    def get(self, request, pk, *args, **kwargs):
        school = self.get_school()
        payment = self.get_object(school, pk)
        return Response(PaymentSerializer(payment).data)


# ── Installment Plans ─────────────────────────────────────────────────────

@extend_schema(tags=["Fees"])
class InstallmentPlanListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = InstallmentPlanSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        qs = InstallmentPlan.objects.filter(
            student_fee__school=school
        ).select_related(
            'student_fee__student',
            'student_fee__fee_structure__fee_type',
        ).prefetch_related('installments')

        status_filter = request.query_params.get('status')
        student_id = request.query_params.get('student')

        if status_filter:
            qs = qs.filter(status=status_filter)
        if student_id:
            qs = qs.filter(student_fee__student_id=student_id)

        serializer = InstallmentPlanSerializer(qs, many=True)
        return Response({'installment_plans': serializer.data, 'count': qs.count()})

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        school = self.get_school()
        serializer = InstallmentPlanCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.save()

        # Auto-generate installment schedule
        student_fee = plan.student_fee
        total = student_fee.amount_charged - student_fee.discount
        amount_per = round(total / plan.number_of_installments, 2)
        today = timezone.localdate()

        for i in range(1, plan.number_of_installments + 1):
            Installment.objects.create(
                plan=plan,
                installment_number=i,
                amount_due=amount_per,
                due_date=today + timedelta(weeks=4 * i),
            )

        return Response(
            {
                'message': f"Installment plan created with {plan.number_of_installments} installments.",
                **InstallmentPlanSerializer(plan).data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Fees"])
class InstallmentPlanDetailView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = InstallmentPlanSerializer

    def get_object(self, school, pk):
        try:
            return InstallmentPlan.objects.get(
                student_fee__school=school, pk=pk
            )
        except InstallmentPlan.DoesNotExist:
            raise NotFound("Installment plan not found.")

    def get(self, request, pk, *args, **kwargs):
        school = self.get_school()
        plan = self.get_object(school, pk)
        return Response(InstallmentPlanSerializer(plan).data)