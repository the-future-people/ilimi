from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

from apps.academics.models import ClassRoom, Term, SubjectAssignment
from apps.reports.models import ReportCard, ReportCardRemark
from apps.reports.services.report_service import (
    generate_report_cards,
    save_remark,
    submit_report_cards,
)
from apps.notifications.services.notification_service import notify_admin_report_submitted
from apps.tenants.models import SchoolMember


def get_teacher_member(request):
    return SchoolMember.objects.get(user=request.user)


@login_required
def teacher_report_generate(request, classroom_id, term_id):
    """
    Generate draft report cards for a classroom/term.
    If already generated, redirect to the student list.
    """
    classroom = get_object_or_404(ClassRoom, id=classroom_id)
    term = get_object_or_404(Term, id=term_id)

    existing = ReportCard.objects.filter(classroom=classroom, term=term)
    if not existing.exists():
        generate_report_cards(
            classroom=classroom,
            term=term,
            generated_by=request.user,
        )

    return redirect('teacher_report_student_list', classroom_id=classroom_id, term_id=term_id)


@login_required
def teacher_report_student_list(request, classroom_id, term_id):
    """
    List all students' report cards for a classroom/term.
    Teacher navigates into each student to preview and add remarks.
    """
    classroom = get_object_or_404(ClassRoom, id=classroom_id)
    term = get_object_or_404(Term, id=term_id)

    report_cards = ReportCard.objects.filter(
        classroom=classroom,
        term=term,
    ).select_related('student', 'remark')

    all_submitted = report_cards.exists() and all(
        rc.status != ReportCard.STATUS_DRAFT for rc in report_cards
    )

    context = {
        'classroom': classroom,
        'term': term,
        'report_cards': report_cards,
        'all_submitted': all_submitted,
    }
    return render(request, 'dashboard/portals/teacher_report_list.html', context)


@login_required
def teacher_report_preview(request, report_card_id):
    """
    Preview a single student's report card.
    Teacher can add/edit their remark here before submitting.
    """
    report_card = get_object_or_404(ReportCard, id=report_card_id)
    entries = report_card.entries.select_related('subject').all()
    remark = getattr(report_card, 'remark', None)

    # Get prev/next student for navigation
    all_cards = list(ReportCard.objects.filter(
        classroom=report_card.classroom,
        term=report_card.term,
    ).order_by('student__last_name', 'student__first_name').values_list('id', flat=True))

    current_index = all_cards.index(report_card.id)
    prev_id = all_cards[current_index - 1] if current_index > 0 else None
    next_id = all_cards[current_index + 1] if current_index < len(all_cards) - 1 else None

    context = {
        'report_card': report_card,
        'entries': entries,
        'remark': remark,
        'prev_id': prev_id,
        'next_id': next_id,
        'current_index': current_index + 1,
        'total': len(all_cards),
    }
    return render(request, 'dashboard/portals/teacher_report_preview.html', context)


@login_required
@require_POST
def teacher_report_save_remark(request, report_card_id):
    """Save teacher's remark for a student's report card via POST."""
    report_card = get_object_or_404(ReportCard, id=report_card_id)

    try:
        data = json.loads(request.body)
        remark_text = data.get('remark', '').strip()
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid data'}, status=400)

    save_remark(
        report_card=report_card,
        remark_text=remark_text,
        teacher=request.user,
    )

    return JsonResponse({'success': True})


@login_required
@require_POST
def teacher_report_submit(request, classroom_id, term_id):
    """
    Submit all draft report cards for a classroom/term for admin evaluation.
    Triggers in-app + SMS notification to admins.
    """
    classroom = get_object_or_404(ClassRoom, id=classroom_id)
    term = get_object_or_404(Term, id=term_id)

    submit_report_cards(classroom=classroom, term=term)

    notify_admin_report_submitted(
        classroom=classroom,
        term=term,
        submitted_by=request.user,
    )

    return JsonResponse({'success': True})