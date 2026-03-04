import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from apps.tenants.models import SchoolMember
from apps.tenants.models import SchoolMember

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