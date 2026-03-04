import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.tenants.models import SchoolMember
from apps.students.models import Student, Guardian, StudentGuardian, EmergencyContact
from apps.academics.models import ClassRoom, AcademicYear

logger = logging.getLogger(__name__)

ENROL_SESSION_KEY = 'student_enrol'
TOTAL_STEPS = 6


def _get_membership(request):
    return SchoolMember.objects.filter(
        user=request.user, is_active=True
    ).select_related('school', 'branch').first()


def _require_admin(request):
    """Returns membership if admin, else None."""
    membership = _get_membership(request)
    if not membership or membership.role not in ('school_admin', 'branch_manager'):
        return None
    return membership


def _base_context(request, membership, current_step=None):
    return {
        'user': request.user,
        'school': membership.school,
        'branch': membership.branch,
        'role': membership.role,
        'role_display': membership.get_role_display(),
        'current_step': current_step,
        'total_steps': TOTAL_STEPS,
    }


def _get_session_data(request):
    return request.session.get(ENROL_SESSION_KEY, {})


def _save_session_data(request, data):
    existing = request.session.get(ENROL_SESSION_KEY, {})
    existing.update(data)
    request.session[ENROL_SESSION_KEY] = existing
    request.session.modified = True


# ── Student List ───────────────────────────────────────────────────────────────

@login_required(login_url='accounts:login')
def student_list(request):
    membership = _require_admin(request)
    if not membership:
        return redirect('dashboard:home')

    school = membership.school
    qs = Student.objects.filter(school=school).select_related(
        'current_class', 'current_class__class_level', 'branch'
    )

    # Filters
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    class_filter = request.GET.get('class', '')

    if search:
        from django.db.models import Q
        qs = qs.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(middle_name__icontains=search) |
            Q(student_id__icontains=search)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)
    if class_filter:
        qs = qs.filter(current_class_id=class_filter)

    classrooms = ClassRoom.objects.filter(
        school=school, is_active=True
    ).select_related('class_level')

    context = _base_context(request, membership)
    context.update({
        'students': qs,
        'total_students': Student.objects.filter(school=school, status='active').count(),
        'total_all': Student.objects.filter(school=school).count(),
        'classrooms': classrooms,
        'search': search,
        'status_filter': status_filter,
        'class_filter': class_filter,
        'status_choices': Student.STATUS_CHOICES,
    })
    return render(request, 'students/student_list.html', context)


# ── Enrolment Wizard ───────────────────────────────────────────────────────────

@login_required(login_url='accounts:login')
def student_enrol_step1(request):
    """Step 1 — Personal Information."""
    membership = _require_admin(request)
    if not membership:
        return redirect('dashboard:home')

    session_data = _get_session_data(request)

    if request.method == 'POST':
        data = {
            'first_name': request.POST.get('first_name', '').strip(),
            'middle_name': request.POST.get('middle_name', '').strip(),
            'last_name': request.POST.get('last_name', '').strip(),
            'date_of_birth': request.POST.get('date_of_birth', ''),
            'gender': request.POST.get('gender', ''),
            'place_of_birth': request.POST.get('place_of_birth', '').strip(),
            'home_town': request.POST.get('home_town', '').strip(),
            'nationality': request.POST.get('nationality', 'Ghanaian').strip(),
            'mother_tongue': request.POST.get('mother_tongue', '').strip(),
            'religion': request.POST.get('religion', ''),
        }
        errors = {}
        if not data['first_name']:
            errors['first_name'] = 'First name is required.'
        if not data['last_name']:
            errors['last_name'] = 'Last name is required.'
        if not data['date_of_birth']:
            errors['date_of_birth'] = 'Date of birth is required.'
        if not data['gender']:
            errors['gender'] = 'Gender is required.'

        if not errors:
            _save_session_data(request, {'step1': data, 'completed_steps': 1})
            return redirect('dashboard:student_enrol_step2')

        context = _base_context(request, membership, current_step=1)
        context.update({'errors': errors, 'form_data': data})
        return render(request, 'students/enrol/step1_personal.html', context)

    context = _base_context(request, membership, current_step=1)
    context['form_data'] = session_data.get('step1', {})
    return render(request, 'students/enrol/step1_personal.html', context)


@login_required(login_url='accounts:login')
def student_enrol_step2(request):
    """Step 2 — Academic Placement."""
    membership = _require_admin(request)
    if not membership:
        return redirect('dashboard:home')

    session_data = _get_session_data(request)
    if not session_data.get('step1'):
        return redirect('dashboard:student_enrol_step1')

    school = membership.school
    classrooms = ClassRoom.objects.filter(
        school=school, is_active=True
    ).select_related('class_level', 'academic_year').order_by(
        'class_level__order', 'section_name'
    )

    if request.method == 'POST':
        data = {
            'enrollment_date': request.POST.get('enrollment_date', ''),
            'current_class_id': request.POST.get('current_class_id', ''),
            'previous_school': request.POST.get('previous_school', '').strip(),
            'expected_graduation_year': request.POST.get('expected_graduation_year', ''),
            'boarding_status': request.POST.get('boarding_status', 'day'),
            'house_dormitory': request.POST.get('house_dormitory', '').strip(),
            'bus_route': request.POST.get('bus_route', '').strip(),
            'locker_number': request.POST.get('locker_number', '').strip(),
        }
        errors = {}
        if not data['enrollment_date']:
            errors['enrollment_date'] = 'Enrollment date is required.'

        if not errors:
            _save_session_data(request, {'step2': data, 'completed_steps': 2})
            return redirect('dashboard:student_enrol_step3')

        context = _base_context(request, membership, current_step=2)
        context.update({
            'errors': errors,
            'form_data': data,
            'classrooms': classrooms,
            'boarding_choices': Student.BOARDING_STATUS_CHOICES,
        })
        return render(request, 'students/enrol/step2_academic.html', context)

    context = _base_context(request, membership, current_step=2)
    context.update({
        'form_data': session_data.get('step2', {}),
        'classrooms': classrooms,
        'boarding_choices': Student.BOARDING_STATUS_CHOICES,
    })
    return render(request, 'students/enrol/step2_academic.html', context)


@login_required(login_url='accounts:login')
def student_enrol_step3(request):
    """Step 3 — Contact & Documents."""
    membership = _require_admin(request)
    if not membership:
        return redirect('dashboard:home')

    session_data = _get_session_data(request)
    if not session_data.get('step2'):
        return redirect('dashboard:student_enrol_step2')

    if request.method == 'POST':
        data = {
            'residential_address': request.POST.get('residential_address', '').strip(),
            'city': request.POST.get('city', '').strip(),
            'region': request.POST.get('region', ''),
            'birth_certificate_number': request.POST.get('birth_certificate_number', '').strip(),
            'nhis_number': request.POST.get('nhis_number', '').strip(),
        }
        _save_session_data(request, {'step3': data, 'completed_steps': 3})
        return redirect('dashboard:student_enrol_step4')

    context = _base_context(request, membership, current_step=3)
    context.update({
        'form_data': session_data.get('step3', {}),
        'region_choices': Student.GHANA_REGIONS,
    })
    return render(request, 'students/enrol/step3_contact.html', context)


@login_required(login_url='accounts:login')
def student_enrol_step4(request):
    """Step 4 — Guardian Information."""
    membership = _require_admin(request)
    if not membership:
        return redirect('dashboard:home')

    session_data = _get_session_data(request)
    if not session_data.get('step3'):
        return redirect('dashboard:student_enrol_step3')

    if request.method == 'POST':
        data = {
            'guardian1_first_name': request.POST.get('guardian1_first_name', '').strip(),
            'guardian1_last_name': request.POST.get('guardian1_last_name', '').strip(),
            'guardian1_relationship': request.POST.get('guardian1_relationship', ''),
            'guardian1_phone': request.POST.get('guardian1_phone', '').strip(),
            'guardian1_whatsapp': request.POST.get('guardian1_whatsapp', '').strip(),
            'guardian1_email': request.POST.get('guardian1_email', '').strip(),
            'guardian1_occupation': request.POST.get('guardian1_occupation', '').strip(),
            'guardian1_employer': request.POST.get('guardian1_employer', '').strip(),
            'guardian1_address': request.POST.get('guardian1_address', '').strip(),
            'guardian1_is_fee_payer': request.POST.get('guardian1_is_fee_payer') == 'on',
            # Optional second guardian
            'guardian2_first_name': request.POST.get('guardian2_first_name', '').strip(),
            'guardian2_last_name': request.POST.get('guardian2_last_name', '').strip(),
            'guardian2_relationship': request.POST.get('guardian2_relationship', ''),
            'guardian2_phone': request.POST.get('guardian2_phone', '').strip(),
            'guardian2_whatsapp': request.POST.get('guardian2_whatsapp', '').strip(),
            'guardian2_email': request.POST.get('guardian2_email', '').strip(),
            'guardian2_occupation': request.POST.get('guardian2_occupation', '').strip(),
            'guardian2_is_fee_payer': request.POST.get('guardian2_is_fee_payer') == 'on',
        }
        errors = {}
        if not data['guardian1_first_name']:
            errors['guardian1_first_name'] = 'Primary guardian first name is required.'
        if not data['guardian1_last_name']:
            errors['guardian1_last_name'] = 'Primary guardian last name is required.'
        if not data['guardian1_phone']:
            errors['guardian1_phone'] = 'Primary guardian phone is required.'
        if not data['guardian1_relationship']:
            errors['guardian1_relationship'] = 'Relationship is required.'

        if not errors:
            _save_session_data(request, {'step4': data, 'completed_steps': 4})
            return redirect('dashboard:student_enrol_step5')

        context = _base_context(request, membership, current_step=4)
        context.update({
            'errors': errors,
            'form_data': data,
            'relationship_choices': Guardian.RELATIONSHIP_CHOICES,
        })
        return render(request, 'students/enrol/step4_guardian.html', context)

    context = _base_context(request, membership, current_step=4)
    context.update({
        'form_data': session_data.get('step4', {}),
        'relationship_choices': Guardian.RELATIONSHIP_CHOICES,
    })
    return render(request, 'students/enrol/step4_guardian.html', context)


@login_required(login_url='accounts:login')
def student_enrol_step5(request):
    """Step 5 — Health & Emergency Contact."""
    membership = _require_admin(request)
    if not membership:
        return redirect('dashboard:home')

    session_data = _get_session_data(request)
    if not session_data.get('step4'):
        return redirect('dashboard:student_enrol_step4')

    if request.method == 'POST':
        data = {
            'blood_group': request.POST.get('blood_group', 'unknown'),
            'known_allergies': request.POST.get('known_allergies', '').strip(),
            'medical_notes': request.POST.get('medical_notes', '').strip(),
            'disability_status': request.POST.get('disability_status') == 'on',
            'disability_description': request.POST.get('disability_description', '').strip(),
            'talents_skills': request.POST.get('talents_skills', '').strip(),
            'additional_notes': request.POST.get('additional_notes', '').strip(),
            # Emergency contact
            'emergency_full_name': request.POST.get('emergency_full_name', '').strip(),
            'emergency_relationship': request.POST.get('emergency_relationship', ''),
            'emergency_phone': request.POST.get('emergency_phone', '').strip(),
            'emergency_whatsapp': request.POST.get('emergency_whatsapp', '').strip(),
        }
        errors = {}
        if not data['emergency_full_name']:
            errors['emergency_full_name'] = 'Emergency contact name is required.'
        if not data['emergency_phone']:
            errors['emergency_phone'] = 'Emergency contact phone is required.'

        if not errors:
            _save_session_data(request, {'step5': data, 'completed_steps': 5})
            return redirect('dashboard:student_enrol_step6')

        context = _base_context(request, membership, current_step=5)
        context.update({
            'errors': errors,
            'form_data': data,
            'blood_group_choices': Student.BLOOD_GROUP_CHOICES,
            'ec_relationship_choices': EmergencyContact.RELATIONSHIP_CHOICES,
        })
        return render(request, 'students/enrol/step5_health.html', context)

    context = _base_context(request, membership, current_step=5)
    context.update({
        'form_data': session_data.get('step5', {}),
        'blood_group_choices': Student.BLOOD_GROUP_CHOICES,
        'ec_relationship_choices': EmergencyContact.RELATIONSHIP_CHOICES,
    })
    return render(request, 'students/enrol/step5_health.html', context)


@login_required(login_url='accounts:login')
def student_enrol_step6(request):
    """Step 6 — Review & Confirm."""
    membership = _require_admin(request)
    if not membership:
        return redirect('dashboard:home')

    session_data = _get_session_data(request)
    if not session_data.get('step5'):
        return redirect('dashboard:student_enrol_step5')

    school = membership.school
    classroom = None
    if session_data.get('step2', {}).get('current_class_id'):
        try:
            classroom = ClassRoom.objects.select_related('class_level').get(
                pk=session_data['step2']['current_class_id'],
                school=school
            )
        except ClassRoom.DoesNotExist:
            pass

    context = _base_context(request, membership, current_step=6)
    context.update({
        'step1': session_data.get('step1', {}),
        'step2': session_data.get('step2', {}),
        'step3': session_data.get('step3', {}),
        'step4': session_data.get('step4', {}),
        'step5': session_data.get('step5', {}),
        'classroom': classroom,
    })
    return render(request, 'students/enrol/step6_review.html', context)


@login_required(login_url='accounts:login')
def student_enrol_submit(request):
    """Final submission — write to database."""
    if request.method != 'POST':
        return redirect('dashboard:student_enrol_step6')

    membership = _require_admin(request)
    if not membership:
        return redirect('dashboard:home')

    session_data = _get_session_data(request)
    school = membership.school

    try:
        s1 = session_data['step1']
        s2 = session_data['step2']
        s3 = session_data['step3']
        s4 = session_data['step4']
        s5 = session_data['step5']
    except KeyError:
        messages.error(request, 'Enrolment session expired. Please start again.')
        return redirect('dashboard:student_enrol_step1')

    from django.db import transaction
    try:
        with transaction.atomic():
            # 1. Create student
            student = Student.objects.create(
                school=school,
                branch=membership.branch,
                first_name=s1['first_name'],
                middle_name=s1.get('middle_name', ''),
                last_name=s1['last_name'],
                date_of_birth=s1['date_of_birth'],
                gender=s1['gender'],
                place_of_birth=s1.get('place_of_birth', ''),
                home_town=s1.get('home_town', ''),
                nationality=s1.get('nationality', 'Ghanaian'),
                mother_tongue=s1.get('mother_tongue', ''),
                religion=s1.get('religion', ''),
                current_class_id=s2.get('current_class_id') or None,
                enrollment_date=s2['enrollment_date'],
                previous_school=s2.get('previous_school', ''),
                expected_graduation_year=s2.get('expected_graduation_year') or None,
                boarding_status=s2.get('boarding_status', 'day'),
                house_dormitory=s2.get('house_dormitory', ''),
                bus_route=s2.get('bus_route', ''),
                locker_number=s2.get('locker_number', ''),
                residential_address=s3.get('residential_address', ''),
                city=s3.get('city', ''),
                region=s3.get('region', ''),
                birth_certificate_number=s3.get('birth_certificate_number', ''),
                nhis_number=s3.get('nhis_number', ''),
                blood_group=s5.get('blood_group', 'unknown'),
                known_allergies=s5.get('known_allergies', ''),
                medical_notes=s5.get('medical_notes', ''),
                disability_status=s5.get('disability_status', False),
                disability_description=s5.get('disability_description', ''),
                talents_skills=s5.get('talents_skills', ''),
                additional_notes=s5.get('additional_notes', ''),
            )

            # 2. Create primary guardian
            guardian1 = Guardian.objects.create(
                first_name=s4['guardian1_first_name'],
                last_name=s4['guardian1_last_name'],
                relationship=s4['guardian1_relationship'],
                phone=s4['guardian1_phone'],
                whatsapp_number=s4.get('guardian1_whatsapp', ''),
                email=s4.get('guardian1_email', ''),
                occupation=s4.get('guardian1_occupation', ''),
                employer=s4.get('guardian1_employer', ''),
                residential_address=s4.get('guardian1_address', ''),
                is_fee_payer=s4.get('guardian1_is_fee_payer', False),
            )
            StudentGuardian.objects.create(
                student=student,
                guardian=guardian1,
                is_primary=True,
            )

            # 3. Create optional second guardian
            if s4.get('guardian2_first_name') and s4.get('guardian2_phone'):
                guardian2 = Guardian.objects.create(
                    first_name=s4['guardian2_first_name'],
                    last_name=s4['guardian2_last_name'],
                    relationship=s4.get('guardian2_relationship', 'other'),
                    phone=s4['guardian2_phone'],
                    whatsapp_number=s4.get('guardian2_whatsapp', ''),
                    email=s4.get('guardian2_email', ''),
                    occupation=s4.get('guardian2_occupation', ''),
                    is_fee_payer=s4.get('guardian2_is_fee_payer', False),
                )
                StudentGuardian.objects.create(
                    student=student,
                    guardian=guardian2,
                    is_primary=False,
                )

            # 4. Create emergency contact
            if s5.get('emergency_full_name') and s5.get('emergency_phone'):
                EmergencyContact.objects.create(
                    student=student,
                    full_name=s5['emergency_full_name'],
                    relationship=s5.get('emergency_relationship', 'other'),
                    phone=s5['emergency_phone'],
                    whatsapp_number=s5.get('emergency_whatsapp', ''),
                    is_primary=True,
                )

        # Clear session
        if ENROL_SESSION_KEY in request.session:
            del request.session[ENROL_SESSION_KEY]

        messages.success(
            request,
            f"{student.full_name} has been successfully enrolled. "
            f"Student ID: {student.student_id}"
        )
        return redirect('dashboard:student_detail', pk=student.pk)

    except Exception as e:
        logger.error(f"Student enrolment error: {str(e)}")
        messages.error(request, f'Enrolment failed: {str(e)}')
        return redirect('dashboard:student_enrol_step6')


# ── Student Detail ─────────────────────────────────────────────────────────────

@login_required(login_url='accounts:login')
def student_detail(request, pk):
    membership = _require_admin(request)
    if not membership:
        return redirect('dashboard:home')

    student = get_object_or_404(
        Student.objects.select_related(
            'current_class', 'current_class__class_level',
            'school', 'branch'
        ).prefetch_related(
            'student_guardians__guardian',
            'emergency_contacts',
        ),
        pk=pk,
        school=membership.school
    )

    context = _base_context(request, membership)
    context['student'] = student
    return render(request, 'students/student_detail.html', context)