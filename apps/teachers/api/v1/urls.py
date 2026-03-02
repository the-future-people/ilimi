from django.urls import path
from .views import (
    StaffProfileListCreateView,
    StaffProfileDetailView,
)

urlpatterns = [
    path('', StaffProfileListCreateView.as_view(), name='staff-list-create'),
    path('<int:pk>/', StaffProfileDetailView.as_view(), name='staff-detail'),
]