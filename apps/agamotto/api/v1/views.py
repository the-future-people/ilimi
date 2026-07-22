from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from drf_spectacular.utils import extend_schema

from apps.agamotto.models import DemoRequest
from .serializers import DemoRequestSerializer


class DemoRequestThrottle(AnonRateThrottle):
    scope = 'demo_request'


@extend_schema(tags=["Agamotto"])
class DemoRequestCreateView(GenericAPIView):
    """
    Public, unauthenticated intake for the landing-page demo form.

    Rate-limited and honeypot-protected. On success, best-effort notifies the
    Ilimi team so the 2-hour reply promise is keepable.
    """

    permission_classes = [AllowAny]
    throttle_classes = [DemoRequestThrottle]
    serializer_class = DemoRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = DemoRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lead = serializer.save(
            source='landing_page',
            ip_address=self._client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:300],
        )

        # Best-effort: a notification failure must never fail the visitor's
        # submission. No-ops cleanly until credentials are wired.
        try:
            from apps.agamotto.services.notify import notify_new_lead
            notify_new_lead(lead)
        except Exception:
            pass

        return Response(
            {'message': "Thank you — we'll be in touch within 2 hours."},
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _client_ip(request):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')