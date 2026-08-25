from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import extend_schema
import json
from rest_framework import status

from apps.core.renderers import IlimiAPIRenderer
from apps.core.models import Position
from apps.tenants.models import SchoolMember
from apps.tenants.api.permissions import HasDomainPermission
from apps.teachers.models import StaffProfile, StaffEmergencyContact
from apps.academics.models import SubjectAssignment
from apps.students.models import Student
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
            'branch', 'position'
        ).prefetch_related('subject_specializations', 'records')

        # Filters
        status_filter = request.query_params.get('status')
        employment_type = request.query_params.get('employment_type')
        staff_category = request.query_params.get('staff_category')
        branch_id = request.query_params.get('branch')
        search = request.query_params.get('search')

        if status_filter:
            qs = qs.filter(status=status_filter)
        if employment_type:
            qs = qs.filter(employment_type=employment_type)
        if staff_category:
            qs = qs.filter(staff_category=staff_category)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if search:
            qs = qs.filter(first_name__icontains=search) | \
                 qs.filter(last_name__icontains=search) | \
                 qs.filter(staff_id__icontains=search) | \
                 qs.filter(phone__icontains=search)

        sort_dir = request.query_params.get('sort_dir', 'asc')
        name_order = ('last_name', 'first_name') if sort_dir == 'asc' else ('-last_name', '-first_name')
        qs = qs.order_by(*name_order)

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

        serializer = StaffProfileListSerializer(page_qs, many=True)
        return Response({
            'staff': serializer.data,
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size if total_count else 0,
            'has_next': end < total_count,
            'has_previous': page > 1,
        })

    def post(self, request, *args, **kwargs):
        member = self.get_member()
        school = member.school
        branch = member.branch

        data = {}
        for key in request.data.keys():
            value = request.data.get(key)
            if key in ('emergency_contacts', 'subject_specializations') and isinstance(value, str):
                try:
                    value = json.loads(value)
                except (ValueError, TypeError):
                    value = []
            data[key] = value

        serializer = StaffProfileCreateSerializer(
            data=data, context={'school': school}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        emergency_contacts_data = data.pop('emergency_contacts', [])
        subject_specializations = data.pop('subject_specializations', [])
        position_name = data.pop('position_name', '').strip()

        position = None
        if position_name:
            position, _ = Position.objects.get_or_create(name=position_name)

        staff = StaffProfile.objects.create(
            school=school,
            branch=branch,
            position=position,
            **data,
        )

        if subject_specializations:
            staff.subject_specializations.set(subject_specializations)

        for ec_data in emergency_contacts_data:
            StaffEmergencyContact.objects.create(staff=staff, **ec_data)

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
    permission_classes = [IsAuthenticated, HasDomainPermission]
    required_domain = 'staff'
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


# ── Current Term for Classroom ────────────────────────────────────────────

@extend_schema(tags=["Staff"])
class ClassroomCurrentTermView(SchoolScopedMixin, GenericAPIView):
    """
    Returns the current term for a given classroom's academic year.
    Used by the teacher portal to know which term to mark attendance for.
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def get(self, request, classroom_id, *args, **kwargs):
        from apps.academics.models import ClassRoom, Term

        school = self.get_school()

        try:
            classroom = ClassRoom.objects.select_related('academic_year').get(
                id=classroom_id, school=school
            )
        except ClassRoom.DoesNotExist:
            return Response({'message': 'Classroom not found.'}, status=404)

        term = Term.objects.filter(
            academic_year=classroom.academic_year, is_current=True
        ).first()

        if not term:
            return Response({
                'term': None,
                'message': 'No active term found for this classroom.',
            })

        return Response({
            'term': {
                'id': term.id,
                'name': term.name,
                'name_display': term.get_name_display(),
                'academic_year': classroom.academic_year.name,
            }
        })


# ── My Classrooms (Teacher Portal) ────────────────────────────────────────

@extend_schema(tags=["Staff"])
class MyClassroomsView(SchoolScopedMixin, GenericAPIView):
    """
    Returns the logged-in teacher's assigned classrooms, one row per
    classroom (not per subject assignment), with real student counts.
    Mirrors the Django teacher_classroom portal view.
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def get(self, request, *args, **kwargs):
        from django.utils import timezone
        from django.db.models import Count
        from apps.attendance.models import AttendanceRegister
        from apps.academics.models import ClassworkRecord

        member = self.get_member()
        today = timezone.localdate()

        from apps.academics.models import ClassRoom

        def build_entry(classroom):
            student_count = Student.objects.filter(
                current_class=classroom,
                school=member.school,
                status='active',
            ).count()

            preview = Student.objects.filter(
                current_class=classroom,
                school=member.school,
                status='active',
            ).order_by('last_name', 'first_name')[:3]

            return {
                'id': classroom.id,
                'full_name': classroom.full_name,
                'class_level': classroom.class_level.display_name,
                'academic_year': classroom.academic_year.name,
                'student_count': student_count,
                'is_form_teacher': classroom.form_teacher_id == member.id,
                'attendance_due': False,
                'unmarked_count': 0,
                'student_preview': [
                    {'id': s.id, 'name': s.full_name} for s in preview
                ],
                'subjects': [],
            }

        classroom_map = {}

        # Form classes first — a form master owns the class whether or not
        # a subject has been assigned to them in it yet.
        form_classes = ClassRoom.objects.filter(
            form_teacher=member, is_active=True
        ).select_related('class_level', 'academic_year')

        for classroom in form_classes:
            classroom_map[classroom.id] = build_entry(classroom)

        assignments = SubjectAssignment.objects.filter(
            teacher=member
        ).select_related(
            'classroom', 'classroom__class_level',
            'classroom__academic_year', 'subject', 'term'
        )

        for a in assignments:
            cid = a.classroom.id
            if cid not in classroom_map:
                classroom_map[cid] = build_entry(a.classroom)

            classroom_map[cid]['subjects'].append({
                'id': a.subject.id,
                'name': a.subject.name,
                'subject_assignment_id': a.id,
                'term_id': a.term_id,
            })

        classroom_ids = list(classroom_map.keys())
        taken_today = set()
        unmarked = []

        if classroom_ids:
            taken_today = set(
                AttendanceRegister.objects.filter(
                    classroom_id__in=classroom_ids,
                    date=today,
                    submitted=True,
                ).values_list('classroom_id', flat=True)
            )
            unmarked = (
                ClassworkRecord.objects.filter(
                    classwork__classroom_id__in=classroom_ids,
                    classwork__due_date__lt=today,
                    status='not_done',
                )
                .values('classwork__classroom_id')
                .annotate(n=Count('id'))
            )

        for cid, data in classroom_map.items():
            if data['is_form_teacher'] and cid not in taken_today:
                data['attendance_due'] = True

        for row in unmarked:
            cid = row['classwork__classroom_id']
            if cid in classroom_map:
                classroom_map[cid]['unmarked_count'] = row['n']

        classrooms = list(classroom_map.values())

        return Response({
            'classrooms': classrooms,
            'count': len(classrooms),
        })

@extend_schema(tags=["Staff"])
class MyStaffProfileView(SchoolScopedMixin, GenericAPIView):
    """
    The requesting user's own staff profile. Deliberately separate from
    StaffProfileDetailView, which is domain-gated: a teacher must be able
    to read her own record without holding staff-domain access.
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]
    serializer_class = StaffProfileSerializer

    def get(self, request, *args, **kwargs):
        member = self.get_member()
        staff = StaffProfile.objects.filter(
            user=request.user, school=member.school
        ).select_related('branch', 'position').prefetch_related(
            'subject_specializations'
        ).first()
        if not staff:
            raise NotFound("No staff profile is linked to your account.")
        return Response(StaffProfileSerializer(staff).data)


@extend_schema(tags=["Staff"])
class ClassroomOverviewView(SchoolScopedMixin, GenericAPIView):
    """
    Class-scoped summary for the teacher's Overview tab: who is away today,
    and who is repeatedly not doing their work.
    """

    permission_classes = [IsAuthenticated]
    renderer_classes = [IlimiAPIRenderer]

    def get(self, request, classroom_id, *args, **kwargs):
        from django.utils import timezone
        from django.db.models import Count, Q
        from apps.academics.models import ClassRoom, Classwork, ClassworkRecord
        from apps.attendance.models import AttendanceRegister

        member = self.get_member()
        today = timezone.localdate()

        try:
            classroom = ClassRoom.objects.get(id=classroom_id, school=member.school)
        except ClassRoom.DoesNotExist:
            raise NotFound("Classroom not found.")

        register = AttendanceRegister.objects.filter(
            classroom=classroom, date=today, submitted=True
        ).first()

        away = []
        if register:
            from apps.attendance.models import StudentAttendance
            rows = StudentAttendance.objects.filter(
                register=register
            ).exclude(status='present').select_related('student')
            away = [
                {
                    'id': r.student.id,
                    'name': r.student.full_name,
                    'status': r.status,
                    'status_display': r.get_status_display(),
                }
                for r in rows
            ]

        # Missing work — only counts tasks that have actually been marked,
        # so unmarked work doesn't make the whole class look delinquent.
        recent = list(
            Classwork.objects.filter(
                classroom=classroom, school=member.school
            ).order_by('-date')[:5]
        )
        counts = {
            r['classwork_id']: r
            for r in ClassworkRecord.objects.filter(classwork__in=recent)
            .values('classwork_id')
            .annotate(
                total=Count('id'),
                not_done=Count('id', filter=Q(status='not_done')),
            )
        }
        marked = [cw for cw in recent if counts.get(cw.id, {}).get('not_done') != counts.get(cw.id, {}).get('total')]

        missing = []
        if len(marked) >= 2:
            rows = (
                ClassworkRecord.objects.filter(
                    classwork__in=marked, status='not_done'
                )
                .values('student_id', 'student__first_name', 'student__last_name')
                .annotate(n=Count('id'))
                .filter(n__gte=2)
                .order_by('-n')[:5]
            )
            missing = [
                {
                    'id': r['student_id'],
                    'name': f"{r['student__first_name']} {r['student__last_name']}",
                    'missed': r['n'],
                    'of': len(marked),
                }
                for r in rows
            ]

        return Response({
            'register_taken': register is not None,
            'away': away,
            'away_count': len(away),
            'missing_work': missing,
            'tasks_considered': len(marked),
        })