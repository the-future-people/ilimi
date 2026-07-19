from django.urls import path
from .views import OccupationSearchView, PositionSearchView

urlpatterns = [
    path('occupations/', OccupationSearchView.as_view(), name='occupation-search'),
    path('positions/', PositionSearchView.as_view(), name='position-search'),
]