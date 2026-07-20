from django.urls import path
from .views import (
    ExcursionListCreateView,
    ExcursionRequestConsentView,
    ConsentRequestListCreateView,
    ConsentRequestPdfView,
    ConsentRequestEmailView,
    ConsentRequestWhatsAppLinkView,
    PublicConsentRequestDetailView,
    PublicConsentRequestRespondView,
)

urlpatterns = [
    path('excursions/', ExcursionListCreateView.as_view(), name='excursion-list-create'),
    path('excursions/<int:pk>/request-consent/', ExcursionRequestConsentView.as_view(), name='excursion-request-consent'),
    path('consent-requests/', ConsentRequestListCreateView.as_view(), name='consent-request-list-create'),
    path('consent-requests/<int:pk>/pdf/', ConsentRequestPdfView.as_view(), name='consent-request-pdf'),
    path('consent-requests/<int:pk>/email/', ConsentRequestEmailView.as_view(), name='consent-request-email'),
    path('consent-requests/<int:pk>/whatsapp/', ConsentRequestWhatsAppLinkView.as_view(), name='consent-request-whatsapp'),
    path('public/consent/<uuid:token>/', PublicConsentRequestDetailView.as_view(), name='public-consent-detail'),
    path('public/consent/<uuid:token>/respond/', PublicConsentRequestRespondView.as_view(), name='public-consent-respond'),
]