from django.urls import path
from .views import OccupationSearchView

urlpatterns = [
    path('occupations/', OccupationSearchView.as_view(), name='occupation-search'),
]