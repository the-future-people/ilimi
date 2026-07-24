from django.urls import path

from .views import (
    PaymentReminderRequestListCreateView,
    PaymentReminderApproveView,
    PaymentReminderDeclineView,
)

urlpatterns = [
    path('payment-reminders/', PaymentReminderRequestListCreateView.as_view(), name='payment-reminder-list-create'),
    path('payment-reminders/<int:pk>/approve/', PaymentReminderApproveView.as_view(), name='payment-reminder-approve'),
    path('payment-reminders/<int:pk>/decline/', PaymentReminderDeclineView.as_view(), name='payment-reminder-decline'),
]