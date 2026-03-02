from django.urls import path
from .views import (
    FeeTypeListCreateView,
    FeeTypeDetailView,
    FeeStructureListCreateView,
    FeeStructureDetailView,
    StudentFeeListCreateView,
    StudentFeeDetailView,
    PaymentListCreateView,
    PaymentDetailView,
    InstallmentPlanListCreateView,
    InstallmentPlanDetailView,
)

urlpatterns = [
    # Fee Types
    path('types/', FeeTypeListCreateView.as_view(), name='fee-type-list-create'),
    path('types/<int:pk>/', FeeTypeDetailView.as_view(), name='fee-type-detail'),

    # Fee Structures
    path('structures/', FeeStructureListCreateView.as_view(), name='fee-structure-list-create'),
    path('structures/<int:pk>/', FeeStructureDetailView.as_view(), name='fee-structure-detail'),

    # Student Fees
    path('student-fees/', StudentFeeListCreateView.as_view(), name='student-fee-list-create'),
    path('student-fees/<int:pk>/', StudentFeeDetailView.as_view(), name='student-fee-detail'),

    # Payments
    path('payments/', PaymentListCreateView.as_view(), name='payment-list-create'),
    path('payments/<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),

    # Installment Plans
    path('installments/', InstallmentPlanListCreateView.as_view(), name='installment-plan-list-create'),
    path('installments/<int:pk>/', InstallmentPlanDetailView.as_view(), name='installment-plan-detail'),
]