from django.urls import path

from .views import (
    AssignmentListCreateView,
    AssignmentCompletionMarkView,
    ParentChildAssignmentsView,
)

urlpatterns = [
    path('assignments/', AssignmentListCreateView.as_view(), name='assignment-list-create'),
    path('completions/<int:pk>/', AssignmentCompletionMarkView.as_view(), name='assignment-completion-mark'),
    path('parent/students/<int:student_id>/assignments/', ParentChildAssignmentsView.as_view(), name='parent-child-assignments'),
]