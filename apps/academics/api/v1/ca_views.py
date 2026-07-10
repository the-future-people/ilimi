from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import extend_schema

from apps.core.renderers import IlimiAPIRenderer
from apps.tenants.models import SchoolMember
from apps.academics.models import (
    CAComponentType, CAComponent, CAComponentScore, CAScore,
    ClassRoom, Subject, Term,
)
from apps.students.models import Student
from .ca_serializers import (
    CAComponentTypeSerializer,
    CAComponentSerializer,
    CAComponentCreateSerializer,
    CAComponentScoreSerializer,
    CAScoreSerializer,
)


class SchoolScopedMixin:
    def get_school(self):
        member = SchoolMember.objects.filter(
            user=self.request.user, is_active=True
        ).select_related('school').first()
        if not member:
            raise NotFound("No active school found for your account.")
        return member.school

    def get_member(self):
        member = SchoolMember.objects.filter(
            user=self.request.user, is_active=True
        ).select_related('school', 'branch').first()
        if not member:
            raise NotFound("No active school found for your account.")
        return member


# ── Component Types ─────────────────────────────────────────────────────

@extend_schema(tags=["CA Scores"])
class CAComponentTypeListView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = CAComponentTypeSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        types = CAComponentType.objects.filter(school=school, is_active=True).order_by('-weight', 'order')
        serializer = CAComponentTypeSerializer(types, many=True)
        return Response({'component_types': serializer.data, 'count': types.count()})


# ── Components ───────────────────────────────────────────────────────────

@extend_schema(tags=["CA Scores"])
class CAComponentListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = CAComponentSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        classroom_id = request.query_params.get('classroom')
        subject_id = request.query_params.get('subject')
        term_id = request.query_params.get('term')

        qs = CAComponent.objects.filter(school=school).select_related('component_type')

        if classroom_id:
            qs = qs.filter(classroom_id=classroom_id)
        if subject_id:
            qs = qs.filter(subject_id=subject_id)
        if term_id:
            qs = qs.filter(term_id=term_id)

        qs = qs.order_by('date', 'name')
        serializer = CAComponentSerializer(qs, many=True)
        return Response({'components': serializer.data, 'count': qs.count()})

    def post(self, request, *args, **kwargs):
        member = self.get_member()
        school = member.school

        serializer = CAComponentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        component = serializer.save(school=school, branch=member.branch, created_by=member)

        return Response({
            'message': f"Component '{component.name}' created successfully.",
            'component': CAComponentSerializer(component).data,
        }, status=status.HTTP_201_CREATED)


# ── Component Scores ───────────────────────────────────────────────────────

@extend_schema(tags=["CA Scores"])
class CAComponentScoreBulkSaveView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, component_id, *args, **kwargs):
        from apps.academics.services.ca_service import save_component_scores, update_ca_score

        member = self.get_member()
        school = member.school

        try:
            component = CAComponent.objects.get(id=component_id, school=school)
        except CAComponent.DoesNotExist:
            raise NotFound("Component not found.")

        score_data = request.data.get('scores', [])

        results, errors = save_component_scores(
            school=school,
            component=component,
            score_data=score_data,
            entered_by=member,
        )

        updated_scores = {}
        for item in score_data:
            student = Student.objects.filter(id=item['student_id'], school=school).first()
            if student:
                ca_score = update_ca_score(
                    school=school,
                    student=student,
                    subject=component.subject,
                    term=component.term,
                    classroom=component.classroom,
                    branch=member.branch,
                )
                updated_scores[student.id] = {
                    'class_score': float(ca_score.class_score),
                    'exam_score': float(ca_score.exam_score),
                    'total': float(ca_score.total),
                    'grade': ca_score.grade,
                }

        return Response({
            'message': f"{len(results)} score(s) saved.",
            'saved': len(results),
            'errors': errors,
            'updated_scores': updated_scores,
        })


# ── CA Scores (summary — class + exam + total) ──────────────────────────

@extend_schema(tags=["CA Scores"])
class CAScoreListView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = CAScoreSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        classroom_id = request.query_params.get('classroom')
        subject_id = request.query_params.get('subject')
        term_id = request.query_params.get('term')

        qs = CAScore.objects.filter(school=school)

        if classroom_id:
            qs = qs.filter(classroom_id=classroom_id)
        if subject_id:
            qs = qs.filter(subject_id=subject_id)
        if term_id:
            qs = qs.filter(term_id=term_id)

        serializer = CAScoreSerializer(qs, many=True)
        return Response({'scores': serializer.data, 'count': qs.count()})


@extend_schema(tags=["CA Scores"])
class CAExamScoreSaveView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, student_id, *args, **kwargs):
        from apps.academics.services.ca_service import save_exam_score

        member = self.get_member()
        school = member.school

        try:
            student = Student.objects.get(id=student_id, school=school)
        except Student.DoesNotExist:
            raise NotFound("Student not found.")

        subject_id = request.data.get('subject')
        term_id = request.data.get('term')
        classroom_id = request.data.get('classroom')
        exam_score = request.data.get('exam_score', 0)

        try:
            subject = Subject.objects.get(id=subject_id, school=school)
            term = Term.objects.get(id=term_id, school=school)
            classroom = ClassRoom.objects.get(id=classroom_id, school=school)
        except (Subject.DoesNotExist, Term.DoesNotExist, ClassRoom.DoesNotExist):
            return Response({'message': 'Invalid subject, term, or classroom.'}, status=400)

        try:
            ca_score = save_exam_score(
                school=school,
                student=student,
                subject=subject,
                term=term,
                exam_score=exam_score,
                classroom=classroom,
                branch=member.branch,
            )
        except ValueError as e:
            return Response({'message': str(e)}, status=400)

        return Response({
            'message': 'Exam score saved.',
            'class_score': float(ca_score.class_score),
            'exam_score': float(ca_score.exam_score),
            'total': float(ca_score.total),
            'grade': ca_score.grade,
        })


@extend_schema(tags=["CA Scores"])
class CAScoresSubmitView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, *args, **kwargs):
        from apps.academics.services.ca_service import submit_ca_scores

        member = self.get_member()
        school = member.school

        classroom_id = request.data.get('classroom')
        subject_id = request.data.get('subject')
        term_id = request.data.get('term')

        try:
            classroom = ClassRoom.objects.get(id=classroom_id, school=school)
            subject = Subject.objects.get(id=subject_id, school=school)
            term = Term.objects.get(id=term_id, school=school)
        except (ClassRoom.DoesNotExist, Subject.DoesNotExist, Term.DoesNotExist):
            return Response({'message': 'Invalid classroom, subject, or term.'}, status=400)

        try:
            submit_ca_scores(
                school=school,
                classroom=classroom,
                subject=subject,
                term=term,
                submitted_by=member,
                branch=member.branch,
            )
        except ValueError as e:
            return Response({'message': str(e)}, status=400)

        return Response({'message': 'Scores submitted and locked successfully.'})