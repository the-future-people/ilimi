from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.core.renderers import IlimiAPIRenderer
from apps.core.models import Occupation
from .serializers import OccupationSerializer


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