from django.urls import path

from .views import DemoRequestCreateView

urlpatterns = [
    path('demo-requests/', DemoRequestCreateView.as_view(), name='demo-request-create'),
]