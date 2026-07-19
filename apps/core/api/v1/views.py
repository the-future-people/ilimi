from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.core.renderers import IlimiAPIRenderer
from apps.core.models import Occupation, Position
from .serializers import OccupationSerializer, PositionSerializer


@extend_schema(tags=["Core"])
class OccupationSearchView(ListAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = OccupationSerializer

    def get_queryset(self):
        qs = Occupation.objects.all()
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(name__icontains=search)
        return qs[:10]


@extend_schema(tags=["Core"])
class PositionSearchView(ListAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = PositionSerializer

    def get_queryset(self):
        qs = Position.objects.all()
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(name__icontains=search)
        return qs[:10]