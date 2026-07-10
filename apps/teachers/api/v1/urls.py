from django.urls import path
from .views import (
    StaffProfileListCreateView,
    StaffProfileDetailView,
    MyClassroomsView,
    ClassroomCurrentTermView,
)

urlpatterns = [
    path('my-classrooms/', MyClassroomsView.as_view(), name='my-classrooms'),
    path('classrooms/<int:classroom_id>/current-term/', ClassroomCurrentTermView.as_view(), name='classroom-current-term'),
    path('', StaffProfileListCreateView.as_view(), name='staff-list-create'),
    path('<int:pk>/', StaffProfileDetailView.as_view(), name='staff-detail'),
]