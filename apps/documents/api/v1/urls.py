from django.urls import path
from .views import (
    DocumentTemplateListCreateView,
    DocumentTemplateDetailView,
    GeneratedDocumentAdminListView,
    StudentGeneratedDocumentListView,
    DocumentPreviewView,
    DocumentGenerateView,
)

urlpatterns = [
    path('templates/', DocumentTemplateListCreateView.as_view(), name='document-template-list-create'),
    path('templates/<int:pk>/', DocumentTemplateDetailView.as_view(), name='document-template-detail'),
    path('students/<int:pk>/documents/', StudentGeneratedDocumentListView.as_view(), name='student-documents-list'),
    path('students/<int:pk>/documents/preview/', DocumentPreviewView.as_view(), name='document-preview'),
    path('students/<int:pk>/documents/generate/', DocumentGenerateView.as_view(), name='document-generate'),
    path('generated/', GeneratedDocumentAdminListView.as_view(), name='generated-document-admin-list'),
]