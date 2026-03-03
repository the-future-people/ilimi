from datetime import datetime, date
from django.utils import timezone
from django.db import transaction

from apps.attendance.models import (
    StudentAttendance,
    StaffAttendance,
    AttendanceSettings,
    AuthorisedPickup,
    PickupIncident,
)
from apps.students.models import Student
from apps.teachers.models import StaffProfile
from apps.tenants.models import School, SchoolMember
from apps.academics.models import Term


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_attendance_settings(school, branch=None):
    """
    Returns the most specific AttendanceSettings available.
    Branch-level settings take priority over school-wide.
    Falls back to safe defaults if none configured.
    """
    if branch:
        settings = AttendanceSettings.objects.filter(
            school=school, branch=branch
        ).first()
        if settings:
            return settings

    return AttendanceSettings.objects.filter(
        school=school, branch__isnull=True
    ).first()


def resolve_attendance_status(clock_in_time, settings):
    """
    Given a clock-in time and school settings, return the correct status.
    Returns 'present' or 'late'.
    """
    if not clock_in_time or not settings:
        return 'present'

    from datetime import timedelta
    start = datetime.combine(date.today(), settings.school_start_time)
    cutoff = start + timedelta(minutes=settings.late_grace_minutes)

    clock_in_dt = datetime.combine(date.today(), clock_in_time)

    if clock_in_dt <= cutoff:
        return 'present'
    return 'late'


def get_active_term(school):
    """Returns the currently active term for the school."""
    today = date.today()
    return Term.objects.filter(
        academic_year__school=school,
        start_date__lte=today,
        end_date__gte=today,
    ).first()


# ── Student Attendance ─────────────────────────────────────────────────────────

@transaction.atomic
def mark_student_attendance(
    school,
    student,
    term,
    status,
    date=None,
    clock_in_time=None,
    source='manual',
    marked_by=None,
    branch=None,
    remarks='',
):
    """
    Create or update a student attendance record for a given date.
    Handles idempotency — if a record already exists for student+date+term,
    it updates rather than duplicates.

    Returns (record, created).
    """
    record_date = date or timezone.localdate()

    # Resolve status automatically if clock_in_time provided and status not forced
    if clock_in_time and status not in ('absent', 'excused'):
        settings = get_attendance_settings(school, branch)
        status = resolve_attendance_status(clock_in_time, settings)

    record, created = StudentAttendance.objects.get_or_create(
        student=student,
        date=record_date,
        term=term,
        defaults={
            'school': school,
            'branch': branch,
            'status': status,
            'source': source,
            'clock_in_time': clock_in_time,
            'via_fingerprint': source == 'fingerprint',
            'locked': source == 'fingerprint',
            'marked_by': marked_by,
            'remarks': remarks,
        }
    )

    if not created:
        # Only update if incoming source is fingerprint and record is manual
        # Fingerprint always wins over manual
        if source == 'fingerprint' or not record.locked:
            record.status = status
            record.source = source
            record.clock_in_time = clock_in_time or record.clock_in_time
            record.via_fingerprint = source == 'fingerprint'
            record.locked = source == 'fingerprint'
            record.marked_by = marked_by or record.marked_by
            record.remarks = remarks or record.remarks
            record.save()

    return record, created


@transaction.atomic
def bulk_mark_student_attendance(
    school,
    term,
    records,
    marked_by=None,
    branch=None,
    date=None,
):
    """
    Bulk mark attendance for a list of students.

    `records` is a list of dicts:
    [
        {'student_id': 1, 'status': 'present', 'clock_in_time': '07:45', 'remarks': ''},
        {'student_id': 2, 'status': 'absent'},
        ...
    ]

    Returns:
    {
        'created': [...],
        'updated': [...],
        'skipped': [...],   # locked fingerprint records not overridden
        'errors': [...],
    }
    """
    record_date = date or timezone.localdate()
    results = {'created': [], 'updated': [], 'skipped': [], 'errors': []}

    settings = get_attendance_settings(school, branch)

    for entry in records:
        try:
            student = Student.objects.get(pk=entry['student_id'], school=school)
            status = entry.get('status', 'absent')
            clock_in_time = entry.get('clock_in_time')
            remarks = entry.get('remarks', '')

            # Parse clock_in_time string if needed
            if isinstance(clock_in_time, str) and clock_in_time:
                from datetime import time as dt_time
                h, m = clock_in_time.split(':')
                clock_in_time = dt_time(int(h), int(m))

            # Auto-resolve status from time if clock-in provided
            if clock_in_time and status not in ('absent', 'excused'):
                status = resolve_attendance_status(clock_in_time, settings)

            existing = StudentAttendance.objects.filter(
                student=student, date=record_date, term=term
            ).first()

            if existing and existing.locked:
                results['skipped'].append({
                    'student_id': student.pk,
                    'name': student.full_name,
                    'reason': 'Locked fingerprint record — cannot override via bulk mark.',
                })
                continue

            record, created = StudentAttendance.objects.update_or_create(
                student=student,
                date=record_date,
                term=term,
                defaults={
                    'school': school,
                    'branch': branch,
                    'status': status,
                    'source': 'manual',
                    'clock_in_time': clock_in_time,
                    'via_fingerprint': False,
                    'locked': False,
                    'marked_by': marked_by,
                    'remarks': remarks,
                }
            )

            if created:
                results['created'].append(student.pk)
            else:
                results['updated'].append(student.pk)

        except Student.DoesNotExist:
            results['errors'].append({
                'student_id': entry.get('student_id'),
                'reason': 'Student not found or does not belong to this school.',
            })
        except Exception as e:
            results['errors'].append({
                'student_id': entry.get('student_id'),
                'reason': str(e),
            })

    return results


@transaction.atomic
def checkout_student(
    attendance_record,
    clock_out_time=None,
    picked_up_by=None,
    pickup_verified_by=None,
    early_dismissal=False,
    early_dismissal_reason='',
    source='manual',
):
    """
    Record a student clock-out / pickup.
    Validates that early dismissal has a reason.
    Returns the updated attendance record.
    """
    now = timezone.localtime()
    record = attendance_record

    # Get school settings to determine if it's early dismissal
    settings = get_attendance_settings(record.school, record.branch)

    checkout_time = clock_out_time or now.time()

    if settings and not early_dismissal:
        checkout_dt = datetime.combine(date.today(), checkout_time)
        close_dt = datetime.combine(date.today(), settings.school_close_time)
        if checkout_dt < close_dt:
            early_dismissal = True

    if early_dismissal and not early_dismissal_reason:
        from rest_framework.exceptions import ValidationError
        raise ValidationError(
            "Early dismissal reason is required when checking out before closing time."
        )

    record.clock_out_time = checkout_time
    record.clock_out_via_fingerprint = source == 'fingerprint'
    record.early_dismissal = early_dismissal
    record.early_dismissal_reason = early_dismissal_reason
    record.picked_up_by = picked_up_by
    record.pickup_verified_by = pickup_verified_by
    record.save()

    return record


@transaction.atomic
def override_locked_record(attendance_record, override_reason, override_by, **fields):
    """
    Allow an admin to override a locked fingerprint record.
    override_reason is mandatory.
    """
    if not override_reason:
        from rest_framework.exceptions import ValidationError
        raise ValidationError("An override reason is required to edit a locked record.")

    record = attendance_record
    for field, value in fields.items():
        setattr(record, field, value)

    record.override_reason = override_reason
    record.override_by = override_by
    record.save()
    return record


# ── Staff Attendance ───────────────────────────────────────────────────────────

@transaction.atomic
def mark_staff_attendance(
    school,
    staff,
    term,
    status,
    date=None,
    clock_in_time=None,
    source='manual',
    branch=None,
    remarks='',
):
    """
    Create or update a staff attendance record.
    Returns (record, created).
    """
    record_date = date or timezone.localdate()

    if clock_in_time and status not in ('absent', 'excused'):
        settings = get_attendance_settings(school, branch)
        status = resolve_attendance_status(clock_in_time, settings)

    record, created = StaffAttendance.objects.get_or_create(
        staff=staff,
        date=record_date,
        term=term,
        defaults={
            'school': school,
            'branch': branch,
            'status': status,
            'source': source,
            'clock_in_time': clock_in_time,
            'via_fingerprint': source == 'fingerprint',
            'locked': source == 'fingerprint',
            'remarks': remarks,
        }
    )

    if not created:
        if source == 'fingerprint' or not record.locked:
            record.status = status
            record.source = source
            record.clock_in_time = clock_in_time or record.clock_in_time
            record.via_fingerprint = source == 'fingerprint'
            record.locked = source == 'fingerprint'
            record.remarks = remarks or record.remarks
            record.save()

    return record, created


@transaction.atomic
def bulk_mark_staff_attendance(
    school,
    term,
    records,
    branch=None,
    date=None,
):
    """
    Bulk mark attendance for a list of staff members.
    Same pattern as bulk_mark_student_attendance.
    """
    record_date = date or timezone.localdate()
    results = {'created': [], 'updated': [], 'skipped': [], 'errors': []}
    settings = get_attendance_settings(school, branch)

    for entry in records:
        try:
            staff = StaffProfile.objects.get(pk=entry['staff_id'], school=school)
            status = entry.get('status', 'absent')
            clock_in_time = entry.get('clock_in_time')
            remarks = entry.get('remarks', '')

            if isinstance(clock_in_time, str) and clock_in_time:
                from datetime import time as dt_time
                h, m = clock_in_time.split(':')
                clock_in_time = dt_time(int(h), int(m))

            if clock_in_time and status not in ('absent', 'excused'):
                status = resolve_attendance_status(clock_in_time, settings)

            existing = StaffAttendance.objects.filter(
                staff=staff, date=record_date, term=term
            ).first()

            if existing and existing.locked:
                results['skipped'].append({
                    'staff_id': staff.pk,
                    'name': staff.full_name,
                    'reason': 'Locked fingerprint record.',
                })
                continue

            record, created = StaffAttendance.objects.update_or_create(
                staff=staff,
                date=record_date,
                term=term,
                defaults={
                    'school': school,
                    'branch': branch,
                    'status': status,
                    'source': 'manual',
                    'clock_in_time': clock_in_time,
                    'via_fingerprint': False,
                    'locked': False,
                    'remarks': remarks,
                }
            )

            if created:
                results['created'].append(staff.pk)
            else:
                results['updated'].append(staff.pk)

        except StaffProfile.DoesNotExist:
            results['errors'].append({
                'staff_id': entry.get('staff_id'),
                'reason': 'Staff member not found.',
            })
        except Exception as e:
            results['errors'].append({
                'staff_id': entry.get('staff_id'),
                'reason': str(e),
            })

    return results


# ── Summary / Reporting ────────────────────────────────────────────────────────

def get_student_attendance_summary(student, term):
    """
    Returns attendance counts and percentage for a student in a term.
    """
    records = StudentAttendance.objects.filter(student=student, term=term)
    total = records.count()

    if total == 0:
        return {
            'total_days': 0,
            'present': 0,
            'absent': 0,
            'late': 0,
            'excused': 0,
            'attendance_percentage': 0.0,
        }

    present = records.filter(status='present').count()
    late = records.filter(status='late').count()
    absent = records.filter(status='absent').count()
    excused = records.filter(status='excused').count()

    # Present + late both count toward attendance percentage
    attendance_percentage = round(((present + late) / total) * 100, 2)

    return {
        'total_days': total,
        'present': present,
        'absent': absent,
        'late': late,
        'excused': excused,
        'attendance_percentage': attendance_percentage,
    }


def get_staff_attendance_summary(staff, term):
    """
    Returns attendance counts and total hours worked for a staff member in a term.
    """
    from django.db.models import Sum
    records = StaffAttendance.objects.filter(staff=staff, term=term)
    total = records.count()

    if total == 0:
        return {
            'total_days': 0,
            'present': 0,
            'absent': 0,
            'late': 0,
            'excused': 0,
            'attendance_percentage': 0.0,
            'total_hours_worked': 0.0,
        }

    present = records.filter(status='present').count()
    late = records.filter(status='late').count()
    absent = records.filter(status='absent').count()
    excused = records.filter(status='excused').count()
    total_hours = records.aggregate(
        total=Sum('hours_worked')
    )['total'] or 0.0

    attendance_percentage = round(((present + late) / total) * 100, 2)

    return {
        'total_days': total,
        'present': present,
        'absent': absent,
        'late': late,
        'excused': excused,
        'attendance_percentage': attendance_percentage,
        'total_hours_worked': float(total_hours),
    }