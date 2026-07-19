from django.urls import path
from .views import (
    GuardianFileUploadView,
    StudentFileUploadView,
    StudentListCreateView,
    StudentDetailView,
    StudentGuardianListCreateView,
    StudentEmergencyContactView,
    StudentClassHistoryView,
    StudentChangeClassView,
    StudentBulkChangeClassView,
    EnrolmentInviteListCreateView,
    EnrolmentInviteApproveView,
    EnrolmentInviteRejectView,
    PublicEnrolmentInviteDetailView,
    PublicEnrolmentInviteSubmitView,
)

urlpatterns = [
    path('', StudentListCreateView.as_view(), name='student-list-create'),
    path('<int:pk>/', StudentDetailView.as_view(), name='student-detail'),
    path('<int:pk>/guardians/', StudentGuardianListCreateView.as_view(), name='student-guardians'),
    path('<int:pk>/emergency-contacts/', StudentEmergencyContactView.as_view(), name='student-emergency-contacts'),
    path('<int:pk>/history/', StudentClassHistoryView.as_view(), name='student-history'),
    path('<int:pk>/change-class/', StudentChangeClassView.as_view(), name='student-change-class'),
    path('bulk-change-class/', StudentBulkChangeClassView.as_view(), name='student-bulk-change-class'),
    path('<int:pk>/upload/<str:field>/', StudentFileUploadView.as_view(), name='student-file-upload'),
    path('guardians/<int:pk>/upload/<str:field>/', GuardianFileUploadView.as_view(), name='guardian-file-upload'),

    # Enrolment invites — admin
    path('invites/', EnrolmentInviteListCreateView.as_view(), name='enrolment-invite-list-create'),
    path('invites/<int:pk>/approve/', EnrolmentInviteApproveView.as_view(), name='enrolment-invite-approve'),
    path('invites/<int:pk>/reject/', EnrolmentInviteRejectView.as_view(), name='enrolment-invite-reject'),

    # Enrolment invites — public, unauthenticated
    path('public/enrol/<uuid:token>/', PublicEnrolmentInviteDetailView.as_view(), name='public-enrolment-invite-detail'),
    path('public/enrol/<uuid:token>/submit/', PublicEnrolmentInviteSubmitView.as_view(), name='public-enrolment-invite-submit'),
]