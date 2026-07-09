from django.urls import path
from .views import (
    StaffProfileListCreateView,
    StaffProfileDetailView,
    MyClassroomsView,
)

urlpatterns = [
    path('my-classrooms/', MyClassroomsView.as_view(), name='my-classrooms'),
    path('', StaffProfileListCreateView.as_view(), name='staff-list-create'),
    path('<int:pk>/', StaffProfileDetailView.as_view(), name='staff-detail'),
]