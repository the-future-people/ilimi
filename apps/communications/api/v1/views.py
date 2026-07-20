from django.utils import timezone
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import extend_schema

from apps.core.renderers import IlimiAPIRenderer
from apps.tenants.models import SchoolMember
from apps.communications.models import Excursion, ConsentRequest
from apps.communications.services.consent import (
    request_excursion_consents,
    create_consent_request,
    respond_to_consent_request,
    generate_consent_pdf,
    send_consent_pdf_email,
    build_whatsapp_share_link,
)
from .serializers import (
    ExcursionSerializer,
    ExcursionCreateSerializer,
    ConsentRequestListSerializer,
    ConsentRequestCreateSerializer,
    ConsentRequestPublicSerializer,
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


@extend_schema(tags=["Communications"])
class ExcursionListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = ExcursionSerializer

    def get(self, request, *args, **kwargs):
        school = self.get_school()
        qs = Excursion.objects.filter(school=school).prefetch_related('classrooms', 'consent_requests')
        serializer = ExcursionSerializer(qs, many=True)
        return Response({'excursions': serializer.data, 'count': qs.count()})

    def post(self, request, *args, **kwargs):
        member = self.get_member()
        serializer = ExcursionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.communications.services.consent import create_excursion
        excursion = create_excursion(member, serializer.validated_data)

        return Response(
            {'message': f"Excursion '{excursion.name}' created.", **ExcursionSerializer(excursion).data},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Communications"])
class ExcursionRequestConsentView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, pk, *args, **kwargs):
        school = self.get_school()
        member = self.get_member()

        try:
            excursion = Excursion.objects.get(school=school, pk=pk)
        except Excursion.DoesNotExist:
            raise NotFound("Excursion not found.")

        base_url = f"{request.scheme}://{request.get_host()}"
        created_count, skipped_count = request_excursion_consents(excursion, member, base_url)

        return Response({
            'message': f"Consent requested for {created_count} student(s).",
            'created_count': created_count,
            'skipped_count': skipped_count,
        })


@extend_schema(tags=["Communications"])
class ConsentRequestListCreateView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = ConsentRequestListSerializer

    def get(self, request, *args, **kwargs):
        from django.db.models import F

        school = self.get_school()
        qs = ConsentRequest.objects.filter(student__school=school).select_related(
            'student__current_class__class_level', 'guardian', 'excursion'
        )
        status_filter = request.query_params.get('status')
        type_filter = request.query_params.get('consent_type')
        method_filter = request.query_params.get('method')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if type_filter:
            qs = qs.filter(consent_type=type_filter)
        if method_filter:
            qs = qs.filter(method=method_filter)

        qs = qs.order_by(
            F('student__current_class__class_level__order').desc(nulls_last=True),
            'student__current_class__section_name', 'student__last_name', 'student__first_name',
        )

        total_count = qs.count()

        try:
            page = max(int(request.query_params.get('page', 1)), 1)
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(max(int(request.query_params.get('page_size', 15)), 1), 100)
        except (TypeError, ValueError):
            page_size = 15

        start = (page - 1) * page_size
        end = start + page_size
        page_qs = qs[start:end]

        serializer = ConsentRequestListSerializer(page_qs, many=True)
        return Response({
            'requests': serializer.data,
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size if total_count else 0,
            'has_next': end < total_count,
            'has_previous': page > 1,
        })

    def post(self, request, *args, **kwargs):
        school = self.get_school()
        member = self.get_member()

        serializer = ConsentRequestCreateSerializer(data=request.data, context={'school': school})
        serializer.is_valid(raise_exception=True)

        base_url = f"{request.scheme}://{request.get_host()}"
        cr = create_consent_request(member, serializer.validated_data, base_url)

        return Response(
            {'message': 'Consent request created.', **ConsentRequestListSerializer(cr).data},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Communications"])
class ConsentRequestPdfView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, pk, *args, **kwargs):
        school = self.get_school()
        try:
            cr = ConsentRequest.objects.get(student__school=school, pk=pk)
        except ConsentRequest.DoesNotExist:
            raise NotFound("Consent request not found.")

        base_url = f"{request.scheme}://{request.get_host()}"
        generate_consent_pdf(cr, base_url=base_url)

        return Response({
            'message': 'PDF generated.',
            'pdf_url': cr.pdf_file.url if cr.pdf_file else None,
        })


@extend_schema(tags=["Communications"])
class ConsentRequestEmailView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, pk, *args, **kwargs):
        school = self.get_school()
        try:
            cr = ConsentRequest.objects.get(student__school=school, pk=pk)
        except ConsentRequest.DoesNotExist:
            raise NotFound("Consent request not found.")

        base_url = f"{request.scheme}://{request.get_host()}"
        sent = send_consent_pdf_email(cr, base_url=base_url)

        if not sent:
            return Response({'message': 'No guardian email on file for this student.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Consent form emailed successfully.'})


@extend_schema(tags=["Communications"])
class ConsentRequestWhatsAppLinkView(SchoolScopedMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, pk, *args, **kwargs):
        school = self.get_school()
        try:
            cr = ConsentRequest.objects.get(student__school=school, pk=pk)
        except ConsentRequest.DoesNotExist:
            raise NotFound("Consent request not found.")

        base_url = f"{request.scheme}://{request.get_host()}"
        result = build_whatsapp_share_link(cr, base_url)

        if not result['whatsapp_link']:
            return Response({'message': 'No guardian phone number on file for this student.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


@extend_schema(tags=["Communications"])
class PublicConsentRequestDetailView(GenericAPIView):
    permission_classes = [AllowAny]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = ConsentRequestPublicSerializer

    def get(self, request, token, *args, **kwargs):
        try:
            cr = ConsentRequest.objects.select_related('student__school', 'excursion').get(token=token)
        except (ConsentRequest.DoesNotExist, ValueError):
            raise NotFound("This consent link is invalid.")

        if cr.status != 'pending':
            return Response({'message': 'This consent request has already been responded to.'}, status=status.HTTP_410_GONE)
        if cr.is_expired:
            cr.status = 'expired'
            cr.save(update_fields=['status'])
            return Response({'message': 'This consent link has expired.'}, status=status.HTTP_410_GONE)

        return Response(ConsentRequestPublicSerializer({
            'school_name': cr.student.school.name,
            'student_name': cr.student.full_name,
            'consent_type': cr.consent_type,
            'consent_type_display': cr.get_consent_type_display(),
            'excursion_name': cr.excursion.name if cr.excursion else None,
            'excursion_description': cr.excursion.description if cr.excursion else None,
            'excursion_date': cr.excursion.date if cr.excursion else None,
            'excursion_location': cr.excursion.location if cr.excursion else None,
        }).data)


@extend_schema(tags=["Communications"])
class PublicConsentRequestRespondView(GenericAPIView):
    permission_classes = [AllowAny]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, token, *args, **kwargs):
        try:
            respond_to_consent_request(
                token=token,
                decision=request.data.get('decision'),
                signed_name=request.data.get('signed_name', ''),
                signature_file=request.FILES.get('signature'),
            )
        except ConsentRequest.DoesNotExist:
            raise NotFound("This consent link is invalid.")
        except ValueError as e:
            reason = str(e)
            if reason == 'already_responded':
                return Response({'message': 'This consent request has already been responded to.'}, status=status.HTTP_410_GONE)
            if reason == 'expired':
                return Response({'message': 'This consent link has expired.'}, status=status.HTTP_410_GONE)
            return Response({'message': "decision must be 'granted' or 'denied'."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': 'Thank you — your response has been recorded.'})