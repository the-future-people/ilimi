from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import extend_schema

from apps.core.renderers import IlimiAPIRenderer
from apps.tenants.models import SchoolMember
from apps.teachers.models import StaffProfile
from .serializers import (
    StaffProfileSerializer,
    StaffProfileListSerializer,
    StaffProfileCreateSerializer,
    StaffProfileUpdateSerializer,
)


# ── Mixin ─────────────────────────────────────────────────────────────────

class SchoolScopedMixin:
    def get_school(self):
        member = SchoolMember.objects.filter(
            user=self.request.user, is_active=True
        ).select_related('school').first()
        if not member:
            raise NotFound("No school found for your account.")
        return member.school

    def get_member(self):
        member = SchoolMember.objects.filter(
            user=self.request.user, is_active=True
        ).select_related('school', 'branch').first()
        if not member:
            raise NotFound("No school found for your account.")
        return member


# ── Staff List + Create ───────────────────────────────────────────────────

@extend_schema(tags=["Staff"])
class StaffProfileListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = StaffProfileSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        qs = StaffProfile.objects.filter(school=school).select_related(
            'branch'
        ).prefetch_related('subject_specializations')

        # Filters
        status_filter = request.query_params.get('status')
        employment_type = request.query_params.get('employment_type')
        branch_id = request.query_params.get('branch')
        search = request.query_params.get('search')

        if status_filter:
            qs = qs.filter(status=status_filter)
        if employment_type:
            qs = qs.filter(employment_type=employment_type)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if search:
            qs = qs.filter(first_name__icontains=search) | \
                 qs.filter(last_name__icontains=search) | \
                 qs.filter(staff_id__icontains=search) | \
                 qs.filter(phone__icontains=search)

        qs = qs.order_by('last_name', 'first_name')
        serializer = StaffProfileListSerializer(qs, many=True)
        return Response({'staff': serializer.data, 'count': qs.count()})

    def post(self, request, *args, **kwargs):
        member = self.get_member()
        school = member.school
        branch = member.branch

        serializer = StaffProfileCreateSerializer(
            data=request.data, context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        staff = serializer.save(school=school, branch=branch)

        return Response(
            {
                'message': f"Staff member '{staff.full_name}' created successfully.",
                **StaffProfileSerializer(staff).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ── Staff Detail + Update ─────────────────────────────────────────────────

@extend_schema(tags=["Staff"])
class StaffProfileDetailView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = StaffProfileSerializer

    def get_object(self, school, pk):
        try:
            return StaffProfile.objects.get(school=school, pk=pk)
        except StaffProfile.DoesNotExist:
            raise NotFound("Staff member not found.")

    def get(self, request, pk, *args, **kwargs):
        school = self.get_school()
        staff = self.get_object(school, pk)
        return Response(StaffProfileSerializer(staff).data)

    def patch(self, request, pk, *args, **kwargs):
        school = self.get_school()
        staff = self.get_object(school, pk)
        serializer = StaffProfileUpdateSerializer(
            staff, data=request.data, partial=True,
            context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'message': 'Staff member updated successfully.',
            **StaffProfileSerializer(staff).data,
        })