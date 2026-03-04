"""
Ilimi Central API Router
All versioned API endpoints are registered here.
"""
from django.urls import path, include

urlpatterns = [
    path("v1/auth/", include("apps.accounts.api.v1.urls", namespace="auth-v1")),
    path("v1/schools/", include("apps.tenants.api.v1.urls", namespace="tenants-v1")),
    path("v1/academics/", include("apps.academics.api.v1.urls")),
    path("v1/students/", include("apps.students.api.v1.urls")),
    path("v1/staff/", include("apps.teachers.api.v1.urls")),
    path("v1/fees/", include("apps.fees.api.v1.urls")),
    path("v1/attendance/", include("apps.attendance.api.v1.urls")),
]