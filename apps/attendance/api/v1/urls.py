from django.urls import path
from .views import (
    AttendanceSettingsView,
    AuthorisedPickupListCreateView,
    AuthorisedPickupDetailView,
    PickupIncidentListCreateView,
    PickupIncidentDetailView,
    StudentAttendanceListCreateView,
    StudentAttendanceBulkView,
    StudentAttendanceDetailView,
    StudentCheckoutView,
    StudentAttendanceSummaryView,
    StaffAttendanceListCreateView,
    StaffAttendanceBulkView,
    StaffAttendanceDetailView,
    StaffAttendanceSummaryView,
    DeviceIngestView,
)

urlpatterns = [
    # Settings
    path('settings/', AttendanceSettingsView.as_view(), name='attendance-settings'),

    # Authorised Pickups
    path('authorised-pickups/', AuthorisedPickupListCreateView.as_view(), name='authorised-pickup-list-create'),
    path('authorised-pickups/<int:pk>/', AuthorisedPickupDetailView.as_view(), name='authorised-pickup-detail'),

    # Pickup Incidents
    path('pickup-incidents/', PickupIncidentListCreateView.as_view(), name='pickup-incident-list-create'),
    path('pickup-incidents/<int:pk>/', PickupIncidentDetailView.as_view(), name='pickup-incident-detail'),

    # Student Attendance
    path('students/', StudentAttendanceListCreateView.as_view(), name='student-attendance-list-create'),
    path('students/bulk/', StudentAttendanceBulkView.as_view(), name='student-attendance-bulk'),
    path('students/summary/', StudentAttendanceSummaryView.as_view(), name='student-attendance-summary'),
    path('students/<int:pk>/', StudentAttendanceDetailView.as_view(), name='student-attendance-detail'),
    path('students/<int:pk>/checkout/', StudentCheckoutView.as_view(), name='student-checkout'),

    # Staff Attendance
    path('staff/', StaffAttendanceListCreateView.as_view(), name='staff-attendance-list-create'),
    path('staff/bulk/', StaffAttendanceBulkView.as_view(), name='staff-attendance-bulk'),
    path('staff/summary/', StaffAttendanceSummaryView.as_view(), name='staff-attendance-summary'),
    path('staff/<int:pk>/', StaffAttendanceDetailView.as_view(), name='staff-attendance-detail'),

    # Device Ingest
    path('ingest/', DeviceIngestView.as_view(), name='device-ingest'),
]