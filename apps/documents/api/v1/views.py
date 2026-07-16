from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from drf_spectacular.utils import extend_schema

from apps.core.renderers import IlimiAPIRenderer
from apps.tenants.models import SchoolMember
from apps.students.models import Student
from apps.documents.models import DocumentTemplate, GeneratedDocument
from apps.documents.services import (
    render_document_html,
    render_pdf,
    build_full_context,
    ExtraFieldValidationError,
)
from .serializers import (
    DocumentTemplateSerializer,
    GeneratedDocumentSerializer,
    GeneratedDocumentAdminListSerializer,
    DocumentGenerationRequestSerializer,
)


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

    def require_admin(self):
        member = self.get_member()
        if member.role != 'school_admin':
            raise PermissionDenied("Only school administrators can manage documents.")
        return member


# ── Document Templates (Admin-only CRUD) ──────────────────────────────

@extend_schema(tags=["Documents"])
class DocumentTemplateListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = DocumentTemplateSerializer

    def get(self, request, *args, **kwargs):
        self.require_admin()
        school = self.get_school()
        qs = DocumentTemplate.objects.filter(school=school).order_by('name')

        document_type = request.query_params.get('document_type')
        is_active = request.query_params.get('is_active')
        if document_type:
            qs = qs.filter(document_type=document_type)
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        self.require_admin()
        school = self.get_school()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(school=school)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Documents"])
class DocumentTemplateDetailView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = DocumentTemplateSerializer

    def get_object(self, pk):
        school = self.get_school()
        try:
            return DocumentTemplate.objects.get(pk=pk, school=school)
        except DocumentTemplate.DoesNotExist:
            raise NotFound("Document template not found.")

    def get(self, request, pk, *args, **kwargs):
        self.require_admin()
        template = self.get_object(pk)
        serializer = self.get_serializer(template)
        return Response(serializer.data)

    def patch(self, request, pk, *args, **kwargs):
        self.require_admin()
        template = self.get_object(pk)
        serializer = self.get_serializer(template, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk, *args, **kwargs):
        self.require_admin()
        template = self.get_object(pk)
        template.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Generated Documents (per-student) ─────────────────────────────────

@extend_schema(tags=["Documents"])
class StudentGeneratedDocumentListView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = GeneratedDocumentSerializer

    def get_student(self, pk):
        school = self.get_school()
        try:
            return Student.objects.get(pk=pk, school=school)
        except Student.DoesNotExist:
            raise NotFound("Student not found.")

    def get(self, request, pk, *args, **kwargs):
        self.require_admin()
        student = self.get_student(pk)
        qs = GeneratedDocument.objects.filter(student=student).select_related(
            'template', 'generated_by'
        )
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

@extend_schema(tags=["Documents"])
class GeneratedDocumentAdminListView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = GeneratedDocumentAdminListSerializer

    def get(self, request, *args, **kwargs):
        self.require_admin()
        school = self.get_school()

        qs = GeneratedDocument.objects.filter(school=school).select_related(
            'student', 'template', 'generated_by'
        )

        document_type = request.query_params.get('document_type')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        search = request.query_params.get('search')

        if document_type:
            qs = qs.filter(template__document_type=document_type)
        if date_from:
            qs = qs.filter(generated_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(generated_at__date__lte=date_to)
        if search:
            qs = qs.filter(student__first_name__icontains=search) | \
                 qs.filter(student__last_name__icontains=search) | \
                 qs.filter(student__student_id__icontains=search)

        qs = qs.order_by('-generated_at')

        total_count = qs.count()

        try:
            page = max(int(request.query_params.get('page', 1)), 1)
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(max(int(request.query_params.get('page_size', 20)), 1), 100)
        except (TypeError, ValueError):
            page_size = 20

        start = (page - 1) * page_size
        end = start + page_size
        page_qs = qs[start:end]

        serializer = self.get_serializer(page_qs, many=True)
        return Response({
            'documents': serializer.data,
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size if total_count else 0,
            'has_next': end < total_count,
            'has_previous': page > 1,
        })

@extend_schema(tags=["Documents"])
class DocumentPreviewView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = DocumentGenerationRequestSerializer

    def post(self, request, pk, *args, **kwargs):
        self.require_admin()
        school = self.get_school()

        try:
            student = Student.objects.get(pk=pk, school=school)
        except Student.DoesNotExist:
            raise NotFound("Student not found.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            template = DocumentTemplate.objects.get(
                pk=data['template_id'], school=school, is_active=True
            )
        except DocumentTemplate.DoesNotExist:
            raise NotFound("Document template not found.")

        try:
            html = render_document_html(student, template, data.get('extra_values'))
        except ExtraFieldValidationError as e:
            return Response(
                {"status": "error", "message": "Missing required fields", "errors": e.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except NotImplementedError as e:
            return Response(
                {"status": "error", "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"html": html})


@extend_schema(tags=["Documents"])
class DocumentGenerateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = DocumentGenerationRequestSerializer

    def post(self, request, pk, *args, **kwargs):
        member = self.require_admin()
        school = self.get_school()

        try:
            student = Student.objects.get(pk=pk, school=school)
        except Student.DoesNotExist:
            raise NotFound("Student not found.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            template = DocumentTemplate.objects.get(
                pk=data['template_id'], school=school, is_active=True
            )
        except DocumentTemplate.DoesNotExist:
            raise NotFound("Document template not found.")

        extra_values = data.get('extra_values') or {}

        try:
            full_context = build_full_context(student, template, extra_values)
            html = render_document_html(student, template, extra_values)
        except ExtraFieldValidationError as e:
            return Response(
                {"status": "error", "message": "Missing required fields", "errors": e.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except NotImplementedError as e:
            return Response(
                {"status": "error", "message": str(e), "errors": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        base_url = request.build_absolute_uri('/')
        pdf_bytes = render_pdf(html, base_url=base_url)

        with transaction.atomic():
            doc = GeneratedDocument.objects.create(
                school=school,
                student=student,
                template=template,
                generated_by=request.user,
                merged_content=html,
                context_snapshot=full_context,
            )
            safe_student_id = student.student_id.replace('/', '-')
            filename = f"{template.document_type}_{safe_student_id}_{doc.id}.pdf"
            doc.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)

        result_serializer = GeneratedDocumentSerializer(doc)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)