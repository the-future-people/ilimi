from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.urls import re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [

    path('admin/', admin.site.urls),

    # Public marketing website
    path('', include('apps.public.urls')),

    # Authentication
    path('accounts/', include('apps.accounts.urls')),

    # Main application
    path('dashboard/', include('apps.dashboard.urls')),

    # Tenants / school onboarding
    path('tenants/', include('apps.tenants.urls')),

    # Reports
    path('reports/', include('apps.reports.urls')),

    # API
    path("api/", include("config.api_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

]

urlpatterns += [
    re_path(
        r'^media/(?P<path>.*)$',
        serve,
        {'document_root': settings.MEDIA_ROOT},
    ),
]