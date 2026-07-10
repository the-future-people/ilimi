from django.urls import path
from .views import (
    AcademicYearListCreateView,
    AcademicYearDetailView,
    TermListCreateView,
    ClassLevelListCreateView,
    ClassRoomListCreateView,
    ClassRoomDetailView,
    SubjectListCreateView,
    SubjectDetailView,
    SubjectAssignmentListCreateView,
    MySchoolClassroomsView,
)
from .ca_views import (
    CAComponentTypeListView,
    CAComponentListCreateView,
    CAComponentScoreBulkSaveView,
    CAScoreListView,
    CAExamScoreSaveView,
    CAScoresSubmitView,
)

urlpatterns = [
    # Academic Years
    path('years/', AcademicYearListCreateView.as_view(), name='academic-year-list'),
    path('years/<int:pk>/', AcademicYearDetailView.as_view(), name='academic-year-detail'),

    # Terms (nested under academic year)
    path('years/<int:year_pk>/terms/', TermListCreateView.as_view(), name='term-list'),

    # Class Levels
    path('class-levels/', ClassLevelListCreateView.as_view(), name='class-level-list'),

    # Classrooms (nested under academic year)
    path('years/<int:year_pk>/classrooms/', ClassRoomListCreateView.as_view(), name='classroom-list'),
    path('classrooms/<int:pk>/', ClassRoomDetailView.as_view(), name='classroom-detail'),

    # Subjects
    path('subjects/', SubjectListCreateView.as_view(), name='subject-list'),
    path('subjects/<int:pk>/', SubjectDetailView.as_view(), name='subject-detail'),

    # Subject Assignments
    path('assignments/', SubjectAssignmentListCreateView.as_view(), name='assignment-list'),

    # CA Scores
    path('ca-component-types/', CAComponentTypeListView.as_view(), name='ca-component-type-list'),
    path('ca-components/', CAComponentListCreateView.as_view(), name='ca-component-list-create'),
    path('ca-components/<int:component_id>/scores/', CAComponentScoreBulkSaveView.as_view(), name='ca-component-scores-save'),
    path('ca-scores/', CAScoreListView.as_view(), name='ca-score-list'),
    path('ca-scores/exam/<int:student_id>/', CAExamScoreSaveView.as_view(), name='ca-exam-score-save'),
    path('ca-scores/submit/', CAScoresSubmitView.as_view(), name='ca-scores-submit'),
    path('my-classrooms/', MySchoolClassroomsView.as_view(), name='my-school-classrooms'),
]