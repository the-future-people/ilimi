import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from apps.tenants.models import SchoolMember
from apps.tenants.models import SchoolMember
import logging
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)


def _get_membership(request):
    """Helper — returns the user's active membership or None."""
    return SchoolMember.objects.filter(
        user=request.user, is_active=True
    ).select_related('school', 'branch').first()


def _base_context(request, membership):
    """Shared context available to all portal templates."""
    return {
        'user': request.user,
        'school': membership.school,
        'branch': membership.branch,
        'role': membership.role,
        'role_display': membership.get_role_display(),
    }


# ── Admin Portal ──────────────────────────────────────────────────────────
@login_required(login_url='accounts:login')
def admin_portal(request):
    membership = _get_membership(request)
    if not membership or membership.role not in ('school_admin', 'branch_manager'):
        return redirect('dashboard:home')

    school = membership.school
    context = _base_context(request, membership)
    context.update({
        'total_members': SchoolMember.objects.filter(school=school, is_active=True).count(),
        'total_branches': school.branches.filter(is_active=True).count(),
        'onboarding_complete': school.onboarding_complete,
        'subscription_status': school.subscription_status,
        'trial_ends_at': school.trial_ends_at,
        'recent_members': SchoolMember.objects.filter(
            school=school, is_active=True
        ).select_related('user').order_by('-id')[:5],
    })
    return render(request, 'dashboard/portals/admin.html', context)

# ── Teacher Portal ────────────────────────────────────────────────────────

@login_required(login_url='accounts:login')
def teacher_portal(request):
    membership = _get_membership(request)
    if not membership or membership.role != 'teacher':
        return redirect('dashboard:home')

    # ── Staff profile ──────────────────────────────────────────────────
    staff_profile = None
    try:
        staff_profile = request.user.staff_profile
    except Exception:
        pass

    # ── Assigned classes via SubjectAssignment ─────────────────────────
    from apps.academics.models import SubjectAssignment
    from apps.students.models import Student

    assignments = SubjectAssignment.objects.filter(
        teacher=membership
    ).select_related('classroom', 'subject', 'term').order_by('classroom__section_name')

    classroom_ids = list(assignments.values_list('classroom_id', flat=True).distinct())

    assigned_classes = list(assignments.values(
        'classroom__id',
        'classroom__section_name',
    ).distinct())

    total_students = Student.objects.filter(
        current_class__id__in=classroom_ids,
        school=membership.school,
        status='active',
    ).count()

    subject_count = assignments.values('subject_id').distinct().count()

    context = _base_context(request, membership)
    context.update({
        'staff_profile': staff_profile,
        'assigned_classes': assigned_classes,
        'classroom_count': len(classroom_ids),
        'total_students': total_students,
        'subject_count': subject_count,
    })
    return render(request, 'dashboard/portals/teacher.html', context)

# ── Accountant Portal ─────────────────────────────────────────────────────

@login_required(login_url='accounts:login')
def accountant_portal(request):
    membership = _get_membership(request)
    if not membership or membership.role != 'accountant':
        return redirect('dashboard:home')

    context = _base_context(request, membership)
    # Placeholders — will be populated when fees are built
    context.update({
        'total_collected': 0,
        'total_outstanding': 0,
        'recent_payments': [],
    })
    return render(request, 'dashboard/portals/accountant.html', context)


# ── Receptionist Portal ───────────────────────────────────────────────────

@login_required(login_url='accounts:login')
def receptionist_portal(request):
    membership = _get_membership(request)
    if not membership or membership.role != 'receptionist':
        return redirect('dashboard:home')

    context = _base_context(request, membership)
    context.update({
        'recent_visitors': [],
        'staff_present_today': 0,
    })
    return render(request, 'dashboard/portals/receptionist.html', context)

# ── Teacher Classroom Landing ─────────────────────────────────────────
@login_required(login_url='accounts:login')
def teacher_classroom(request):
    membership = _get_membership(request)
    if not membership or membership.role != 'teacher':
        return redirect('dashboard:home')

    staff_profile = None
    try:
        staff_profile = request.user.staff_profile
    except Exception:
        pass

    from apps.academics.models import SubjectAssignment
    from apps.students.models import Student

    assignments = SubjectAssignment.objects.filter(
        teacher=membership
    ).select_related(
        'classroom', 'classroom__class_level',
        'classroom__academic_year', 'subject', 'term'
    ).order_by('classroom__class_level__order', 'classroom__section_name')

    # Build a rich class list for the template
    classroom_ids = list(assignments.values_list('classroom_id', flat=True).distinct())

    # Per-classroom student count
    from django.db.models import Count
    classrooms_data = []
    seen = set()
    for a in assignments:
        cid = a.classroom.id
        if cid in seen:
            continue
        seen.add(cid)
        student_count = Student.objects.filter(
            current_class=a.classroom,
            school=membership.school,
            status='active',
        ).count()
        classrooms_data.append({
            'classroom': a.classroom,
            'student_count': student_count,
        })

    context = _base_context(request, membership)
    context.update({
        'staff_profile': staff_profile,
        'classrooms_data': classrooms_data,
        'classroom_count': len(classrooms_data),
    })
    return render(request, 'dashboard/portals/teacher_classroom.html', context)


@login_required(login_url='accounts:login')
def teacher_class_detail(request, classroom_id):
    membership = _get_membership(request)
    if not membership or membership.role != 'teacher':
        return redirect('dashboard:home')

    staff_profile = None
    try:
        staff_profile = request.user.staff_profile
    except Exception:
        pass

    from apps.academics.models import SubjectAssignment, ClassRoom, Term
    from apps.students.models import Student

    # Verify this teacher is actually assigned to this classroom
    classroom = get_object_or_404(
        ClassRoom,
        id=classroom_id,
        school=membership.school,
    )

    assigned = SubjectAssignment.objects.filter(
        teacher=membership,
        classroom=classroom,
    ).exists()

    if not assigned:
        return redirect('dashboard:teacher_classroom')

    # Subjects this teacher teaches in this class
    subjects = SubjectAssignment.objects.filter(
        teacher=membership,
        classroom=classroom,
    ).select_related('subject', 'term').order_by('subject__name')

    # Current term
    current_term = Term.objects.filter(
        academic_year=classroom.academic_year,
        is_current=True,
    ).first()

    # Student roster
    students = Student.objects.filter(
        current_class=classroom,
        school=membership.school,
        status='active',
    ).order_by('last_name', 'first_name')

    context = _base_context(request, membership)
    context.update({
        'staff_profile': staff_profile,
        'classroom': classroom,
        'subjects': subjects,
        'current_term': current_term,
        'students': students,
        'student_count': students.count(),
    })
    return render(request, 'dashboard/portals/teacher_class_detail.html', context)