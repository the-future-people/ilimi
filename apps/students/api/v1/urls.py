from django.urls import path
from .views import (
    StudentListCreateView,
    StudentDetailView,
    StudentGuardianListCreateView,
    StudentEmergencyContactView,
    StudentClassHistoryView,
    StudentChangeClassView,
    StudentBulkChangeClassView,
)

urlpatterns = [
    path('', StudentListCreateView.as_view(), name='student-list-create'),
    path('<int:pk>/', StudentDetailView.as_view(), name='student-detail'),
    path('<int:pk>/guardians/', StudentGuardianListCreateView.as_view(), name='student-guardians'),
    path('<int:pk>/emergency-contacts/', StudentEmergencyContactView.as_view(), name='student-emergency-contacts'),
    path('<int:pk>/history/', StudentClassHistoryView.as_view(), name='student-history'),
    path('<int:pk>/change-class/', StudentChangeClassView.as_view(), name='student-change-class'),
    path('bulk-change-class/', StudentBulkChangeClassView.as_view(), name='student-bulk-change-class'),
]