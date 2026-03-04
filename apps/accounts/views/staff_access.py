import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.http import JsonResponse

from apps.accounts.models import StaffPortalInvite
from apps.accounts.services.staff_invite import send_staff_portal_invite, accept_staff_invite
from apps.teachers.models import StaffProfile
from apps.tenants.models import SchoolMember

logger = logging.getLogger(__name__)


@login_required(login_url='accounts:login')
def send_invite(request, staff_pk):
    """Admin triggers a portal invite for a staff member."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed.'}, status=405)

    membership = SchoolMember.objects.filter(
        user=request.user, is_active=True
    ).select_related('school').first()

    if not membership or membership.role not in ('school_admin', 'branch_manager'):
        return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)

    staff = get_object_or_404(StaffProfile, pk=staff_pk, school=membership.school)

    success, message = send_staff_portal_invite(
        staff=staff,
        invited_by=request.user,
        request=request,
    )

    return JsonResponse({'success': success, 'message': message})


def staff_setup_account(request, token):
    """Staff member clicks SMS link and sets their password."""

    try:
        invite = StaffPortalInvite.objects.select_related(
            'staff', 'staff__user'
        ).get(token=token)
    except StaffPortalInvite.DoesNotExist:
        return render(request, 'accounts/staff_invite_invalid.html', {
            'reason': 'invalid'
        })

    if not invite.is_valid:
        return render(request, 'accounts/staff_invite_invalid.html', {
            'reason': 'expired' if invite.is_expired else 'used'
        })

    if request.method == 'POST':
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        errors = {}

        if not password1:
            errors['password1'] = 'Password is required.'
        elif len(password1) < 8:
            errors['password1'] = 'Password must be at least 8 characters.'
        if password1 != password2:
            errors['password2'] = 'Passwords do not match.'

        if not errors:
            success, message, user = accept_staff_invite(str(token), password1)
            if success and user:
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                return redirect('dashboard:teacher_portal')
            else:
                errors['general'] = message

        return render(request, 'accounts/staff_setup_account.html', {
            'invite': invite,
            'staff': invite.staff,
            'errors': errors,
        })

    return render(request, 'accounts/staff_setup_account.html', {
        'invite': invite,
        'staff': invite.staff,
        'errors': {},
    })