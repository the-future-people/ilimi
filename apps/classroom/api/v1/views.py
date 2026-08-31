from apps.core.scoping import SchoolScopedMixin
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import extend_schema

from apps.core.renderers import IlimiAPIRenderer
from apps.tenants.models import SchoolMember
from apps.students.models import Guardian
from apps.classroom.models import Assignment, AssignmentCompletion
from apps.classroom.services.assignments import create_assignment, mark_completion, submit_completion

from .serializers import AssignmentSerializer, AssignmentCreateSerializer, AssignmentCompletionSerializer


@extend_schema(tags=["Classroom"])
class AssignmentListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = AssignmentSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        qs = Assignment.objects.filter(
            subject_assignment__classroom__school=school
        ).select_related(
            'subject_assignment__subject', 'subject_assignment__classroom', 'created_by__user'
        ).prefetch_related('completions__student')

        subject_assignment_id = request.query_params.get('subject_assignment')
        if subject_assignment_id:
            qs = qs.filter(subject_assignment_id=subject_assignment_id)

        serializer = AssignmentSerializer(qs, many=True)
        return Response({'assignments': serializer.data, 'count': qs.count()})

    def post(self, request, *args, **kwargs):
        school = self.get_school()
        member = self.get_member()

        serializer = AssignmentCreateSerializer(data=request.data, context={'school': school})
        serializer.is_valid(raise_exception=True)

        assignment = create_assignment(created_by=member, **serializer.validated_data)
        return Response(
            {
                'message': f"'{assignment.title}' posted.",
                **AssignmentSerializer(assignment).data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Classroom"])
class AssignmentCompletionMarkView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = AssignmentCompletionSerializer

    def patch(self, request, pk, *args, **kwargs):
        school = self.get_school()
        member = self.get_member()

        try:
            completion = AssignmentCompletion.objects.select_related('assignment').get(
                pk=pk, assignment__subject_assignment__classroom__school=school
            )
        except AssignmentCompletion.DoesNotExist:
            raise NotFound("Completion record not found.")

        new_status = request.data.get('status')
        if new_status:
            mark_completion(completion, status=new_status, marked_by=member)

        return Response({
            'message': 'Updated.',
            **AssignmentCompletionSerializer(completion).data,
        })


@extend_schema(tags=["Classroom"])
class ParentChildAssignmentsView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = AssignmentSerializer

    def get(self, request, student_id, *args, **kwargs):
        guardian = Guardian.objects.filter(user=request.user).first()
        if not guardian:
            raise NotFound("No guardian profile linked to your account.")

        link_exists = guardian.student_guardians.filter(student_id=student_id).exists()
        if not link_exists:
            raise NotFound("This student is not linked to your account.")

        qs = Assignment.objects.filter(
            subject_assignment__classroom__students__id=student_id
        ).select_related(
            'subject_assignment__subject', 'subject_assignment__classroom', 'created_by__user'
        ).distinct()

        results = []
        for assignment in qs:
            data = AssignmentSerializer(assignment).data
            own_completion = assignment.completions.filter(student_id=student_id).first()
            data['completions'] = (
                [AssignmentCompletionSerializer(own_completion).data] if own_completion else []
            )
            results.append(data)

        return Response({'assignments': results, 'count': len(results)})
