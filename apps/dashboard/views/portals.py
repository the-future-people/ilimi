import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from apps.tenants.models import SchoolMember
from apps.academics.models import SubjectAssignment, ClassRoom, Term, Subject
from apps.students.models import Student
from apps.attendance.models import StudentAttendance, AttendanceRegister
from apps.attendance.services.attendance_service import get_or_create_register
from django.utils import timezone

logger = logging.getLogger(__name__)


def _get_membership(request):
    return SchoolMember.objects.filter(
        user=request.user, is_active=True
    ).select_related('school', 'branch').first()


def _base_context(request, membership):
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
    from apps.notifications.services.notification_service import get_unread_count
    from apps.notifications.models import Notification

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
        'unread_count': get_unread_count(request.user, school),
        'notifications': Notification.objects.filter(
            recipient=request.user,
            school=school,
        ).order_by('-created_at')[:10],
    })
    return render(request, 'dashboard/portals/admin.html', context)


# ── Teacher Portal ────────────────────────────────────────────────────────
@login_required(login_url='accounts:login')
def teacher_portal(request):
    membership = _get_membership(request)
    if not membership or membership.role != 'teacher':
        return redirect('dashboard:home')

    staff_profile = None
    try:
        staff_profile = request.user.staff_profile
    except Exception:
        pass

    assignments = SubjectAssignment.objects.filter(
        teacher=membership
    ).select_related('classroom', 'subject', 'term').order_by('classroom__section_name')

    classroom_ids = list(assignments.values_list('classroom_id', flat=True).distinct())

    total_students = Student.objects.filter(
        current_class__id__in=classroom_ids,
        school=membership.school,
        status='active',
    ).count()

    subject_count = assignments.values('subject_id').distinct().count()

    context = _base_context(request, membership)
    context.update({
        'staff_profile': staff_profile,
        'assigned_classes': list(assignments.values('classroom__id', 'classroom__section_name').distinct()),
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


# ── Teacher Classroom Landing ─────────────────────────────────────────────
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

    assignments = SubjectAssignment.objects.filter(
        teacher=membership
    ).select_related(
        'classroom', 'classroom__class_level',
        'classroom__academic_year', 'subject', 'term'
    ).order_by('classroom__class_level__order', 'classroom__section_name')

    classroom_ids = list(assignments.values_list('classroom_id', flat=True).distinct())

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


# ── Teacher Class Detail ──────────────────────────────────────────────────
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

    classroom = get_object_or_404(ClassRoom, id=classroom_id, school=membership.school)

    assigned = SubjectAssignment.objects.filter(
        teacher=membership,
        classroom=classroom,
    ).exists()

    if not assigned:
        return redirect('dashboard:teacher_classroom')

    subjects = SubjectAssignment.objects.filter(
        teacher=membership,
        classroom=classroom,
    ).select_related('subject', 'term').order_by('subject__name')

    current_term = Term.objects.filter(
        academic_year=classroom.academic_year,
        is_current=True,
    ).first()

    students = Student.objects.filter(
        current_class=classroom,
        school=membership.school,
        status='active',
    ).order_by('last_name', 'first_name')

    # Attendance data for today
    today = timezone.localdate()
    attendance_register = None
    student_rows = []

    if current_term:
        attendance_register, _ = get_or_create_register(
            school=membership.school,
            classroom=classroom,
            term=current_term,
            date=today,
            branch=membership.branch,
        )

        existing_records = StudentAttendance.objects.filter(
            student__in=students,
            date=today,
            term=current_term,
        ).select_related('student')

        existing_map = {r.student_id: r for r in existing_records}

        for student in students:
            record = existing_map.get(student.id)
            student_rows.append({
                'student': student,
                'status': record.status if record else '',
                'source': record.source if record else '',
                'locked': record.locked if record else False,
                'clock_in_time': record.clock_in_time if record else None,
                'remarks': record.remarks if record else '',
            })

    context = _base_context(request, membership)
    context.update({
        'staff_profile': staff_profile,
        'classroom': classroom,
        'subjects': subjects,
        'current_term': current_term,
        'students': students,
        'student_count': students.count(),
        'today': today,
        'attendance_register': attendance_register,
        'student_rows': student_rows,
        'statuses': [
            ('present', 'Present', '<svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>'),
            ('absent', 'Absent', '<svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>'),
            ('late', 'Late', '<svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'),
            ('excused', 'Excused', '<svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>'),
        ],
    })
    return render(request, 'dashboard/portals/teacher_class_detail.html', context)


# ── Teacher Daily Attendance ──────────────────────────────────────────────
@login_required(login_url='accounts:login')
def teacher_attendance(request, classroom_id):
    membership = _get_membership(request)
    if not membership or membership.role != 'teacher':
        return redirect('dashboard:home')

    staff_profile = None
    try:
        staff_profile = request.user.staff_profile
    except Exception:
        pass

    classroom = get_object_or_404(ClassRoom, id=classroom_id, school=membership.school)

    if not SubjectAssignment.objects.filter(teacher=membership, classroom=classroom).exists():
        return redirect('dashboard:teacher_classroom')

    current_term = Term.objects.filter(
        academic_year=classroom.academic_year,
        is_current=True,
    ).first()

    if not current_term:
        context = _base_context(request, membership)
        context.update({
            'staff_profile': staff_profile,
            'classroom': classroom,
            'error': 'No active term found. Please contact your administrator.',
        })
        return render(request, 'dashboard/portals/teacher_attendance.html', context)

    today = timezone.localdate()

    register, _ = get_or_create_register(
        school=membership.school,
        classroom=classroom,
        term=current_term,
        date=today,
        branch=membership.branch,
    )

    students = Student.objects.filter(
        current_class=classroom,
        school=membership.school,
        status='active',
    ).order_by('last_name', 'first_name')

    existing_records = StudentAttendance.objects.filter(
        student__in=students,
        date=today,
        term=current_term,
    ).select_related('student')

    existing_map = {r.student_id: r for r in existing_records}

    student_rows = []
    for student in students:
        record = existing_map.get(student.id)
        student_rows.append({
            'student': student,
            'status': record.status if record else None,
            'source': record.source if record else None,
            'locked': record.locked if record else False,
            'clock_in_time': record.clock_in_time if record else None,
            'remarks': record.remarks if record else '',
        })

    context = _base_context(request, membership)
    context.update({
        'staff_profile': staff_profile,
        'classroom': classroom,
        'current_term': current_term,
        'today': today,
        'register': register,
        'student_rows': student_rows,
        'student_count': students.count(),
    })
    return render(request, 'dashboard/portals/teacher_attendance.html', context)


# ── Teacher Attendance Submit ─────────────────────────────────────────────
@login_required(login_url='accounts:login')
def teacher_attendance_submit(request, classroom_id):
    if request.method != 'POST':
        return redirect('dashboard:teacher_attendance', classroom_id=classroom_id)

    membership = _get_membership(request)
    if not membership or membership.role != 'teacher':
        return redirect('dashboard:home')

    from apps.attendance.services.attendance_service import submit_register
    import json

    classroom = get_object_or_404(ClassRoom, id=classroom_id, school=membership.school)

    current_term = Term.objects.filter(
        academic_year=classroom.academic_year,
        is_current=True,
    ).first()

    if not current_term:
        return redirect('dashboard:teacher_attendance', classroom_id=classroom_id)

    try:
        data = json.loads(request.body)
        records = data.get('records', [])

        register, results = submit_register(
            school=membership.school,
            classroom=classroom,
            term=current_term,
            records=records,
            submitted_by=membership,
            date=timezone.localdate(),
            branch=membership.branch,
        )

        return JsonResponse({
            'success': True,
            'message': f'Register submitted. {register.total_present} present, {register.total_absent} absent.',
            'total_present': register.total_present,
            'total_absent': register.total_absent,
            'total_late': register.total_late,
            'total_excused': register.total_excused,
        })

    except ValueError as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'Something went wrong.'}, status=500)

# ── Teacher CA Scores ─────────────────────────────────────────────────────
@login_required(login_url='accounts:login')
def teacher_ca_scores(request, classroom_id, subject_id):
    membership = _get_membership(request)
    if not membership or membership.role != 'teacher':
        return redirect('dashboard:home')

    staff_profile = None
    try:
        staff_profile = request.user.staff_profile
    except Exception:
        pass

    from apps.academics.models import CAComponent, CAComponentType, CAScore
    from apps.academics.services.ca_service import get_default_component_types

    classroom = get_object_or_404(ClassRoom, id=classroom_id, school=membership.school)
    subject   = get_object_or_404(Subject, id=subject_id, school=membership.school)

    if not SubjectAssignment.objects.filter(teacher=membership, classroom=classroom, subject=subject).exists():
        return redirect('dashboard:teacher_classroom')

    current_term = Term.objects.filter(
        academic_year=classroom.academic_year,
        is_current=True,
    ).first()

    students = Student.objects.filter(
        current_class=classroom,
        school=membership.school,
        status='active',
    ).order_by('last_name', 'first_name')

    # Components for this subject/term
    components = CAComponent.objects.filter(
        school=membership.school,
        classroom=classroom,
        subject=subject,
        term=current_term,
    ).select_related('component_type').order_by('date', 'name') if current_term else []

    # Component types available for this school
    component_types = get_default_component_types(membership.school)

    # CA Scores
    ca_scores = {}
    if current_term:
        from apps.academics.models import CAComponentScore
        for student in students:
            scores_qs = CAComponentScore.objects.filter(
                student=student,
                component__in=components,
                school=membership.school,
            ).select_related('component')
            scores_map = {s.component_id: s for s in scores_qs}

            ca_score_obj = CAScore.objects.filter(
                student=student,
                subject=subject,
                term=current_term,
                school=membership.school,
            ).first()

            ca_scores[student.id] = {
                'component_scores': scores_map,
                'class_score': float(ca_score_obj.class_score) if ca_score_obj else 0,
                'exam_score': float(ca_score_obj.exam_score) if ca_score_obj else 0,
                'total': float(ca_score_obj.total) if ca_score_obj else 0,
                'grade': ca_score_obj.grade if ca_score_obj else '',
                'locked': ca_score_obj.locked if ca_score_obj else False,
                'submitted': ca_score_obj.submitted if ca_score_obj else False,
            }

    all_submitted = all(
        ca_scores[s.id]['submitted'] for s in students
    ) if students and ca_scores else False

    context = _base_context(request, membership)
    context.update({
        'staff_profile': staff_profile,
        'classroom': classroom,
        'subject': subject,
        'current_term': current_term,
        'students': students,
        'student_count': students.count(),
        'components': components,
        'component_types': component_types,
        'ca_scores': ca_scores,
        'all_submitted': all_submitted,
    })
    return render(request, 'dashboard/portals/teacher_ca_scores.html', context)


@login_required(login_url='accounts:login')
def teacher_ca_component_create(request, classroom_id, subject_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method.'}, status=405)

    membership = _get_membership(request)
    if not membership or membership.role != 'teacher':
        return JsonResponse({'success': False, 'message': 'Unauthorised.'}, status=403)

    from apps.academics.models import CAComponentType
    from apps.academics.services.ca_service import create_ca_component
    import json

    classroom = get_object_or_404(ClassRoom, id=classroom_id, school=membership.school)
    subject   = get_object_or_404(Subject, id=subject_id, school=membership.school)

    current_term = Term.objects.filter(
        academic_year=classroom.academic_year,
        is_current=True,
    ).first()

    if not current_term:
        return JsonResponse({'success': False, 'message': 'No active term.'}, status=400)

    try:
        data             = json.loads(request.body)
        component_type   = get_object_or_404(CAComponentType, id=data.get('component_type_id'), school=membership.school)
        name             = data.get('name', '').strip()
        max_score        = data.get('max_score', 100)
        date             = data.get('date')

        if not name:
            return JsonResponse({'success': False, 'message': 'Component name is required.'}, status=400)

        component = create_ca_component(
            school=membership.school,
            classroom=classroom,
            subject=subject,
            term=current_term,
            component_type=component_type,
            name=name,
            max_score=max_score,
            date=date,
            created_by=membership,
            branch=membership.branch,
        )

        return JsonResponse({
            'success': True,
            'component_id': component.id,
            'name': component.name,
            'max_score': float(component.max_score),
            'date': str(component.date),
            'component_type': component.component_type.name,
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required(login_url='accounts:login')
def teacher_ca_scores_save(request, classroom_id, subject_id, component_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method.'}, status=405)

    membership = _get_membership(request)
    if not membership or membership.role != 'teacher':
        return JsonResponse({'success': False, 'message': 'Unauthorised.'}, status=403)

    from apps.academics.models import CAComponent
    from apps.academics.services.ca_service import save_component_scores, update_ca_score
    import json

    classroom = get_object_or_404(ClassRoom, id=classroom_id, school=membership.school)
    subject   = get_object_or_404(Subject, id=subject_id, school=membership.school)
    component = get_object_or_404(CAComponent, id=component_id, school=membership.school)

    current_term = Term.objects.filter(
        academic_year=classroom.academic_year,
        is_current=True,
    ).first()

    if not current_term:
        return JsonResponse({'success': False, 'message': 'No active term.'}, status=400)

    try:
        data       = json.loads(request.body)
        score_data = data.get('scores', [])

        results, errors = save_component_scores(
            school=membership.school,
            component=component,
            score_data=score_data,
            entered_by=membership,
        )

        # Recompute class scores for affected students
        updated_scores = {}
        for item in score_data:
            student = Student.objects.filter(id=item['student_id'], school=membership.school).first()
            if student:
                ca_score = update_ca_score(
                    school=membership.school,
                    student=student,
                    subject=subject,
                    term=current_term,
                    classroom=classroom,
                    branch=membership.branch,
                )
                updated_scores[student.id] = {
                    'class_score': float(ca_score.class_score),
                    'exam_score': float(ca_score.exam_score),
                    'total': float(ca_score.total),
                    'grade': ca_score.grade,
                }

        return JsonResponse({
            'success': True,
            'saved': len(results),
            'errors': errors,
            'updated_scores': updated_scores,
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required(login_url='accounts:login')
def teacher_ca_exam_score_save(request, classroom_id, subject_id, student_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method.'}, status=405)

    membership = _get_membership(request)
    if not membership or membership.role != 'teacher':
        return JsonResponse({'success': False, 'message': 'Unauthorised.'}, status=403)

    from apps.academics.services.ca_service import save_exam_score
    import json

    classroom = get_object_or_404(ClassRoom, id=classroom_id, school=membership.school)
    subject   = get_object_or_404(Subject, id=subject_id, school=membership.school)
    student   = get_object_or_404(Student, id=student_id, school=membership.school)

    current_term = Term.objects.filter(
        academic_year=classroom.academic_year,
        is_current=True,
    ).first()

    if not current_term:
        return JsonResponse({'success': False, 'message': 'No active term.'}, status=400)

    try:
        data       = json.loads(request.body)
        exam_score = data.get('exam_score', 0)

        ca_score = save_exam_score(
            school=membership.school,
            student=student,
            subject=subject,
            term=current_term,
            exam_score=exam_score,
            classroom=classroom,
            branch=membership.branch,
        )

        return JsonResponse({
            'success': True,
            'exam_score': float(ca_score.exam_score),
            'class_score': float(ca_score.class_score),
            'total': float(ca_score.total),
            'grade': ca_score.grade,
        })

    except ValueError as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'Something went wrong.'}, status=500)


@login_required(login_url='accounts:login')
def teacher_ca_scores_submit(request, classroom_id, subject_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method.'}, status=405)

    membership = _get_membership(request)
    if not membership or membership.role != 'teacher':
        return JsonResponse({'success': False, 'message': 'Unauthorised.'}, status=403)

    from apps.academics.services.ca_service import submit_ca_scores

    classroom = get_object_or_404(ClassRoom, id=classroom_id, school=membership.school)
    subject   = get_object_or_404(Subject, id=subject_id, school=membership.school)

    current_term = Term.objects.filter(
        academic_year=classroom.academic_year,
        is_current=True,
    ).first()

    if not current_term:
        return JsonResponse({'success': False, 'message': 'No active term.'}, status=400)

    try:
        submit_ca_scores(
            school=membership.school,
            classroom=classroom,
            subject=subject,
            term=current_term,
            submitted_by=membership,
            branch=membership.branch,
        )
        return JsonResponse({'success': True, 'message': 'Scores submitted and locked successfully.'})

    except ValueError as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'Something went wrong.'}, status=500)