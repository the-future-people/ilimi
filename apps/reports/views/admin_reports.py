from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

from apps.reports.models import ReportCard
from apps.reports.services.report_service import approve_report_card, release_report_cards
from apps.notifications.services.notification_service import (
    get_unread_count,
    mark_all_read,
    mark_notification_read,
)
from apps.notifications.models import Notification
from apps.tenants.models import SchoolMember
from apps.academics.models import ClassRoom, Term


def _get_admin_membership(request):
    return SchoolMember.objects.filter(
        user=request.user,
        role__in=('school_admin', 'branch_manager'),
        is_active=True,
    ).select_related('school', 'branch').first()


@login_required
def admin_report_queue(request):
    """
    Admin view — list all classrooms with submitted report cards pending review.
    """
    membership = _get_admin_membership(request)
    if not membership:
        return redirect('dashboard:admin_portal')

    school = membership.school

    # Get all submitted/approved report cards grouped by classroom + term
    submitted_cards = ReportCard.objects.filter(
        school=school,
        status__in=[ReportCard.STATUS_SUBMITTED, ReportCard.STATUS_APPROVED],
    ).select_related('classroom', 'term', 'classroom__class_level').order_by(
        'classroom__class_level__order', 'term'
    )

    # Group by classroom + term
    groups = {}
    for rc in submitted_cards:
        key = (rc.classroom.id, rc.term.id)
        if key not in groups:
            groups[key] = {
                'classroom': rc.classroom,
                'term': rc.term,
                'total': 0,
                'submitted': 0,
                'approved': 0,
                'all_approved': False,
            }
        groups[key]['total'] += 1
        if rc.status == ReportCard.STATUS_SUBMITTED:
            groups[key]['submitted'] += 1
        elif rc.status == ReportCard.STATUS_APPROVED:
            groups[key]['approved'] += 1

    for key in groups:
        g = groups[key]
        g['all_approved'] = g['submitted'] == 0 and g['approved'] == g['total']

    unread_count = get_unread_count(request.user, school)
    notifications = Notification.objects.filter(
        recipient=request.user,
        school=school,
    ).order_by('-created_at')[:10]

    context = {
        'user': request.user,
        'school': school,
        'branch': membership.branch,
        'report_groups': list(groups.values()),
        'unread_count': unread_count,
        'notifications': notifications,
    }
    return render(request, 'dashboard/portals/admin_report_queue.html', context)


@login_required
def admin_report_class_review(request, classroom_id, term_id):
    """
    Admin view — review all student report cards for a classroom/term.
    """
    membership = _get_admin_membership(request)
    if not membership:
        return redirect('dashboard:admin_portal')

    school = membership.school
    classroom = get_object_or_404(ClassRoom, id=classroom_id, school=school)
    term = get_object_or_404(Term, id=term_id)

    report_cards = ReportCard.objects.filter(
        school=school,
        classroom=classroom,
        term=term,
    ).select_related('student', 'remark').order_by(
        'student__last_name', 'student__first_name'
    )

    all_approved = report_cards.exists() and all(
        rc.status == ReportCard.STATUS_APPROVED for rc in report_cards
    )

    unread_count = get_unread_count(request.user, school)

    context = {
        'user': request.user,
        'school': school,
        'branch': membership.branch,
        'classroom': classroom,
        'term': term,
        'report_cards': report_cards,
        'all_approved': all_approved,
        'unread_count': unread_count,
    }
    return render(request, 'dashboard/portals/admin_report_class_review.html', context)


@login_required
def admin_report_student_review(request, report_card_id):
    """
    Admin view — review a single student's report card, add head's comment, approve.
    """
    membership = _get_admin_membership(request)
    if not membership:
        return redirect('dashboard:admin_portal')

    report_card = get_object_or_404(ReportCard, id=report_card_id, school=membership.school)
    entries = report_card.entries.select_related('subject').all()
    remark = getattr(report_card, 'remark', None)

    # Prev/next navigation
    all_cards = list(ReportCard.objects.filter(
        classroom=report_card.classroom,
        term=report_card.term,
        school=membership.school,
    ).order_by('student__last_name', 'student__first_name').values_list('id', flat=True))

    current_index = all_cards.index(report_card.id)
    prev_id = all_cards[current_index - 1] if current_index > 0 else None
    next_id = all_cards[current_index + 1] if current_index < len(all_cards) - 1 else None

    unread_count = get_unread_count(request.user, membership.school)

    context = {
        'user': request.user,
        'school': membership.school,
        'branch': membership.branch,
        'report_card': report_card,
        'entries': entries,
        'remark': remark,
        'prev_id': prev_id,
        'next_id': next_id,
        'current_index': current_index + 1,
        'total': len(all_cards),
        'unread_count': unread_count,
    }
    return render(request, 'dashboard/portals/admin_report_student_review.html', context)


@login_required
@require_POST
def admin_report_approve(request, report_card_id):
    """Approve a single report card and save head's comment."""
    membership = _get_admin_membership(request)
    if not membership:
        return JsonResponse({'success': False, 'error': 'Unauthorised'}, status=403)

    report_card = get_object_or_404(ReportCard, id=report_card_id, school=membership.school)

    try:
        data = json.loads(request.body)
        head_comment = data.get('head_comment', '').strip()
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid data'}, status=400)

    if not head_comment:
        return JsonResponse({'success': False, 'error': 'Head comment is required.'}, status=400)

    approve_report_card(
        report_card=report_card,
        approved_by=request.user,
        head_comment=head_comment,
    )

    return JsonResponse({'success': True})


@login_required
@require_POST
def admin_report_release(request, classroom_id, term_id):
    """Release all approved report cards for a classroom/term to parents."""
    membership = _get_admin_membership(request)
    if not membership:
        return JsonResponse({'success': False, 'error': 'Unauthorised'}, status=403)

    classroom = get_object_or_404(ClassRoom, id=classroom_id, school=membership.school)
    term = get_object_or_404(Term, id=term_id)

    released = release_report_cards(classroom=classroom, term=term)

    return JsonResponse({'success': True, 'released': len(released)})


@login_required
@require_POST
def admin_notifications_mark_read(request):
    """Mark single or all notifications as read for the current admin."""
    membership = _get_admin_membership(request)
    if not membership:
        return JsonResponse({'success': False}, status=403)

    try:
        data = json.loads(request.body)
        notification_id = data.get('notification_id')
    except (json.JSONDecodeError, AttributeError):
        notification_id = None

    if notification_id:
        from apps.notifications.services.notification_service import mark_single_read
        mark_single_read(notification_id=notification_id, user=request.user)
    else:
        mark_all_read(user=request.user, school=membership.school)

    return JsonResponse({'success': True})