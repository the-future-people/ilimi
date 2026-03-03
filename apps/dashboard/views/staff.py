import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from apps.tenants.models import SchoolMember
from apps.teachers.models import StaffProfile
from apps.dashboard.forms.staff_forms import (
    StaffPersonalForm,
    StaffContactForm,
    StaffEmploymentForm,
    StaffQualificationForm,
    StaffDocumentsBankingForm,
    StaffNextOfKinForm,
)

logger = logging.getLogger(__name__)

STAFF_SESSION_KEY = 'staff_enrol'
TOTAL_STEPS = 6


def _get_membership(request):
    return SchoolMember.objects.filter(
        user=request.user, is_active=True
    ).select_related('school', 'branch').first()


def _require_admin(request):
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
    return request.session.get(STAFF_SESSION_KEY, {})


def _save_session_data(request, data):
    existing = request.session.get(STAFF_SESSION_KEY, {})
    existing.update(data)
    request.session[STAFF_SESSION_KEY] = existing
    request.session.modified = True


# ── Staff List ─────────────────────────────────────────────────────────────────

@login_required(login_url='accounts:login')
def staff_list(request):
    membership = _require_admin(request)
    if not membership:
        return redirect('dashboard:home')

    school = membership.school
    qs = StaffProfile.objects.filter(school=school).select_related('branch')

    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')

    if search:
        from django.db.models import Q
        qs = qs.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(middle_name__icontains=search) |
            Q(staff_id__icontains=search) |
            Q(phone__icontains=search)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)
    if type_filter:
        qs = qs.filter(employment_type=type_filter)

    context = _base_context(request, membership)
    context.update({
        'staff': qs,
        'total_active': StaffProfile.objects.filter(school=school, status='active').count(),
        'total_all': StaffProfile.objects.filter(school=school).count(),
        'search': search,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'status_choices': StaffProfile.STATUS_CHOICES,
        'type_choices': StaffProfile.EMPLOYMENT_TYPE_CHOICES,
    })
    return render(request, 'staff/staff_list.html', context)


# ── Registration Wizard ────────────────────────────────────────────────────────

@login_required(login_url='accounts:login')
def staff_register_step1(request):
    """Step 1 — Personal Information."""
    membership = _require_admin(request)
    if not membership:
        return redirect('dashboard:home')

    session_data = _get_session_data(request)
    initial = session_data.get('step1', {})

    if request.method == 'POST':
        form = StaffPersonalForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data.copy()
            # DateField → string for session serialization
            if data.get('date_of_birth'):
                data['date_of_birth'] = data['date_of_birth'].isoformat()
            # Don't store file in session — handle photo separately
            data.pop('photo', None)
            _save_session_data(request, {'step1': data})
            # Store photo in session files if uploaded
            if 'photo' in request.FILES:
                request.session['staff_photo_name'] = request.FILES['photo'].name
            return redirect('dashboard:staff_register_step2')
        context = _base_context(request, membership, current_step=1)
        context['form'] = form
        return render(request, 'staff/register/step1_personal.html', context)

    form = StaffPersonalForm(initial=initial)
    context = _base_context(request, membership, current_step=1)
    context['form'] = form
    return render(request, 'staff/register/step1_personal.html', context)


@login_required(login_url='accounts:login')
def staff_register_step2(request):
    """Step 2 — Contact & Address."""
    membership = _require_admin(request)
    if not membership:
        return redirect('dashboard:home')

    session_data = _get_session_data(request)
    if not session_data.get('step1'):
        return redirect('dashboard:staff_register_step1')

    initial = session_data.get('step2', {})

    if request.method == 'POST':
        form = StaffContactForm(request.POST)
        if form.is_valid():
            form.validate_phone_unique(school=membership.school)
            if form.is_valid():  # re-check after uniqueness
                _save_session_data(request, {'step2': form.cleaned_data})
                return redirect('dashboard:staff_register_step3')
        context = _base_context(request, membership, current_step=2)
        context['form'] = form
        return render(request, 'staff/register/step2_contact.html', context)

    form = StaffContactForm(initial=initial)
    context = _base_context(request, membership, current_step=2)
    context['form'] = form
    return render(request, 'staff/register/step2_contact.html', context)


@login_required(login_url='accounts:login')
def staff_register_step3(request):
    """Step 3 — Employment."""
    membership = _require_admin(request)
    if not membership:
        return redirect('dashboard:home')

    session_data = _get_session_data(request)
    if not session_data.get('step2'):
        return redirect('dashboard:staff_register_step2')

    initial = session_data.get('step3', {})

    if request.method == 'POST':
        form = StaffEmploymentForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data.copy()
            # Serialize dates
            for field in ['date_joined_school', 'date_of_first_appointment', 'probation_end_date']:
                if data.get(field):
                    data[field] = data[field].isoformat()
            _save_session_data(request, {'step3': data})
            return redirect('dashboard:staff_register_step4')
        context = _base_context(request, membership, current_step=3)
        context['form'] = form
        return render(request, 'staff/register/step3_employment.html', context)

    form = StaffEmploymentForm(initial=initial)
    context = _base_context(request, membership, current_step=3)
    context['form'] = form
    return render(request, 'staff/register/step3_employment.html', context)


@login_required(login_url='accounts:login')
def staff_register_step4(request):
    """Step 4 — Qualifications & Specializations."""
    membership = _require_admin(request)
    if not membership:
        return redirect('dashboard:home')

    session_data = _get_session_data(request)
    if not session_data.get('step3'):
        return redirect('dashboard:staff_register_step3')

    initial = session_data.get('step4', {})

    if request.method == 'POST':
        form = StaffQualificationForm(request.POST, school=membership.school)
        if form.is_valid():
            data = form.cleaned_data.copy()
            # Store subject IDs (M2M — can't store objects in session)
            subjects = data.pop('subject_specializations', [])
            data['subject_specialization_ids'] = [s.id for s in subjects]
            _save_session_data(request, {'step4': data})
            return redirect('dashboard:staff_register_step5')
        context = _base_context(request, membership, current_step=4)
        context['form'] = form
        return render(request, 'staff/register/step4_qualifications.html', context)

    form = StaffQualificationForm(initial=initial, school=membership.school)
    context = _base_context(request, membership, current_step=4)
    context['form'] = form
    return render(request, 'staff/register/step4_qualifications.html', context)


@login_required(login_url='accounts:login')
def staff_register_step5(request):
    """Step 5 — Documents & Banking."""
    membership = _require_admin(request)
    if not membership:
        return redirect('dashboard:home')

    session_data = _get_session_data(request)
    if not session_data.get('step4'):
        return redirect('dashboard:staff_register_step4')

    initial = session_data.get('step5', {})

    if request.method == 'POST':
        form = StaffDocumentsBankingForm(request.POST)
        if form.is_valid():
            form.validate_unique_documents(school=membership.school)
            if form.is_valid():
                _save_session_data(request, {'step5': form.cleaned_data})
                return redirect('dashboard:staff_register_step6')
        context = _base_context(request, membership, current_step=5)
        context['form'] = form
        return render(request, 'staff/register/step5_documents.html', context)

    form = StaffDocumentsBankingForm(initial=initial)
    context = _base_context(request, membership, current_step=5)
    context['form'] = form
    return render(request, 'staff/register/step5_documents.html', context)


@login_required(login_url='accounts:login')
def staff_register_step6(request):
    """Step 6 — Next of Kin & Review."""
    membership = _require_admin(request)
    if not membership:
        return redirect('dashboard:home')

    session_data = _get_session_data(request)
    if not session_data.get('step5'):
        return redirect('dashboard:staff_register_step5')

    initial = session_data.get('step6', {})

    if request.method == 'POST':
        form = StaffNextOfKinForm(request.POST)
        if form.is_valid():
            _save_session_data(request, {'step6': form.cleaned_data})
            return redirect('dashboard:staff_register_review')
        context = _base_context(request, membership, current_step=6)
        context['form'] = form
        return render(request, 'staff/register/step6_nextofkin.html', context)

    form = StaffNextOfKinForm(initial=initial)
    context = _base_context(request, membership, current_step=6)
    context['form'] = form
    return render(request, 'staff/register/step6_nextofkin.html', context)


@login_required(login_url='accounts:login')
def staff_register_review(request):
    """Review — show summary before final submit."""
    membership = _require_admin(request)
    if not membership:
        return redirect('dashboard:home')

    session_data = _get_session_data(request)
    if not session_data.get('step6'):
        return redirect('dashboard:staff_register_step6')

    context = _base_context(request, membership, current_step=7)
    context.update({
        'step1': session_data.get('step1', {}),
        'step2': session_data.get('step2', {}),
        'step3': session_data.get('step3', {}),
        'step4': session_data.get('step4', {}),
        'step5': session_data.get('step5', {}),
        'step6': session_data.get('step6', {}),
    })
    return render(request, 'staff/register/review.html', context)


@login_required(login_url='accounts:login')
def staff_register_submit(request):
    """Final submission — write to database."""
    if request.method != 'POST':
        return redirect('dashboard:staff_register_review')

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
        s6 = session_data['step6']
    except KeyError:
        messages.error(request, 'Session expired. Please start again.')
        return redirect('dashboard:staff_register_step1')

    try:
        with transaction.atomic():
            staff = StaffProfile.objects.create(
                school=school,
                branch=membership.branch,
                # Step 1
                first_name=s1['first_name'],
                middle_name=s1.get('middle_name', ''),
                last_name=s1['last_name'],
                date_of_birth=s1.get('date_of_birth') or None,
                gender=s1['gender'],
                nationality=s1.get('nationality', 'Ghanaian'),
                marital_status=s1.get('marital_status', ''),
                number_of_dependants=s1.get('number_of_dependants', 0),
                # Step 2
                phone=s2['phone'],
                whatsapp_number=s2.get('whatsapp_number', ''),
                email=s2.get('email', ''),
                residential_address=s2.get('residential_address', ''),
                city=s2.get('city', ''),
                region=s2.get('region', ''),
                # Step 3
                employment_type=s3['employment_type'],
                date_joined_school=s3.get('date_joined_school') or None,
                date_of_first_appointment=s3.get('date_of_first_appointment') or None,
                salary_grade=s3.get('salary_grade', ''),
                is_on_probation=s3.get('is_on_probation', False),
                probation_end_date=s3.get('probation_end_date') or None,
                is_head_of_department=s3.get('is_head_of_department', False),
                # Step 4
                highest_qualification=s4.get('highest_qualification', ''),
                institution_attended=s4.get('institution_attended', ''),
                years_of_experience=s4.get('years_of_experience', 0),
                ntc_license_number=s4.get('ntc_license_number', ''),
                # Step 5
                ghana_card_number=s5.get('ghana_card_number', ''),
                ssnit_number=s5.get('ssnit_number', ''),
                bank_name=s5.get('bank_name', ''),
                bank_branch=s5.get('bank_branch', ''),
                bank_account_number=s5.get('bank_account_number', ''),
                momo_number=s5.get('momo_number', ''),
                # Step 6
                next_of_kin_name=s6.get('next_of_kin_name', ''),
                next_of_kin_relationship=s6.get('next_of_kin_relationship', ''),
                next_of_kin_phone=s6.get('next_of_kin_phone', ''),
                next_of_kin_address=s6.get('next_of_kin_address', ''),
            )

            # M2M subject specializations
            subject_ids = s4.get('subject_specialization_ids', [])
            if subject_ids:
                staff.subject_specializations.set(subject_ids)

        # Clear session
        # Clear session
        for key in [STAFF_SESSION_KEY, 'staff_photo_name']:
            request.session.pop(key, None)

        request.session['staff_success'] = {
            'name': staff.full_name,
            'staff_id': staff.staff_id,
        }
        return redirect('dashboard:staff_list')

    except Exception as e:
        logger.error(f"Staff registration error: {str(e)}")
        messages.error(request, f'Registration failed: {str(e)}')
        return redirect('dashboard:staff_register_review')


# ── Staff Detail ───────────────────────────────────────────────────────────────

@login_required(login_url='accounts:login')
def staff_detail(request, pk):
    membership = _require_admin(request)
    if not membership:
        return redirect('dashboard:home')

    staff = get_object_or_404(
        StaffProfile.objects.select_related('school', 'branch')
        .prefetch_related('subject_specializations'),
        pk=pk,
        school=membership.school
    )

    context = _base_context(request, membership)
    context['staff'] = staff
    return render(request, 'staff/staff_detail.html', context)

@login_required(login_url='accounts:login')
def clear_staff_toast(request):
    if request.method == 'POST':
        request.session.pop('staff_success', None)
    from django.http import JsonResponse
    return JsonResponse({'ok': True})