from celery import shared_task
from django.utils import timezone


# ── Student Attendance Tasks ───────────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # retry after 60 seconds
    name='attendance.notify_guardian_checkin',
)
def task_notify_guardian_checkin(self, attendance_id):
    """
    Sends check-in SMS to guardians for a student attendance record.
    Retries up to 3 times on failure with 60s delay.
    """
    try:
        from apps.attendance.models import StudentAttendance
        from apps.attendance.services.sms_service import notify_guardian_checkin

        record = StudentAttendance.objects.select_related(
            'student', 'school', 'branch'
        ).get(pk=attendance_id)

        notify_guardian_checkin(record.student, record)

    except StudentAttendance.DoesNotExist:
        # Record deleted before task ran — do not retry
        return
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name='attendance.notify_guardian_checkout',
)
def task_notify_guardian_checkout(self, attendance_id):
    """
    Sends checkout SMS to guardians when a student is collected.
    """
    try:
        from apps.attendance.models import StudentAttendance
        from apps.attendance.services.sms_service import notify_guardian_checkout

        record = StudentAttendance.objects.select_related(
            'student', 'school', 'branch', 'picked_up_by'
        ).get(pk=attendance_id)

        notify_guardian_checkout(record.student, record)

    except StudentAttendance.DoesNotExist:
        return
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    name='attendance.notify_guardian_absence',
)
def task_notify_guardian_absence(self, student_id, school_id):
    """
    Sends absence SMS to primary guardian.
    Triggered by Celery Beat at absence_notify_time for students
    who have no attendance record for today.
    """
    try:
        from apps.students.models import Student
        from apps.tenants.models import School
        from apps.attendance.services.sms_service import notify_guardian_absence

        student = Student.objects.get(pk=student_id)
        school = School.objects.get(pk=school_id)
        notify_guardian_absence(student, school)

    except (Student.DoesNotExist, Exception) as exc:
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    name='attendance.notify_unclocked_out',
)
def task_notify_unclocked_out(self, attendance_id):
    """
    Alerts class teacher and guardian for students still on campus
    past the unclocked_out_alert_time with no clock-out recorded.
    """
    try:
        from apps.attendance.models import StudentAttendance
        from apps.attendance.services.sms_service import (
            notify_guardian_checkin,
            send_sms,
            build_unclocked_out_sms,
        )

        record = StudentAttendance.objects.select_related(
            'student', 'school', 'branch'
        ).get(pk=attendance_id)

        # Only alert if still not clocked out
        if record.is_clocked_out:
            return

        # SMS guardian
        message = build_unclocked_out_sms(record.student, record.school)
        from apps.students.models import StudentGuardian
        guardians = StudentGuardian.objects.filter(
            student=record.student
        ).select_related('guardian')
        for sg in guardians:
            if sg.guardian.phone:
                send_sms(sg.guardian.phone, message)

        # TODO: Notify class teacher via in-app notification
        # when notification system is built

    except StudentAttendance.DoesNotExist:
        return
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Pickup Incident Tasks ──────────────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,  # urgent — shorter retry
    name='attendance.notify_pickup_authorisation',
)
def task_notify_pickup_authorisation(self, incident_id):
    """
    Sends authorisation SMS to primary guardian when an
    unrecognised person attempts to collect a student.
    Short retry delay — this is time-critical.
    """
    try:
        from apps.attendance.models import PickupIncident
        from apps.attendance.services.sms_service import notify_pickup_authorisation

        incident = PickupIncident.objects.select_related(
            'student', 'school'
        ).get(pk=incident_id)

        notify_pickup_authorisation(incident)

    except PickupIncident.DoesNotExist:
        return
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Celery Beat Periodic Tasks ─────────────────────────────────────────────────

@shared_task(name='attendance.sweep_absences')
def task_sweep_absences():
    """
    Periodic task — runs daily at absence_notify_time (via Celery Beat).
    Finds all students with no attendance record for today and
    queues an absence notification for each.

    Beat schedule (add to settings.py when Celery is configured):

    from celery.schedules import crontab
    CELERY_BEAT_SCHEDULE = {
        'sweep-absences': {
            'task': 'attendance.sweep_absences',
            'schedule': crontab(hour=9, minute=0),
        },
        'sweep-unclocked-out': {
            'task': 'attendance.sweep_unclocked_out',
            'schedule': crontab(hour=15, minute=30),
        },
    }
    """
    from datetime import date
    from apps.tenants.models import School
    from apps.students.models import Student, StudentGuardian
    from apps.attendance.models import StudentAttendance, AttendanceSettings

    today = date.today()

    for school in School.objects.filter(is_active=True):
        # Get all active students for this school
        all_students = Student.objects.filter(school=school, status='active')

        # Get students who already have a record today
        checked_in_ids = StudentAttendance.objects.filter(
            school=school, date=today
        ).values_list('student_id', flat=True)

        # Queue absence notification for those who haven't checked in
        absent_students = all_students.exclude(pk__in=checked_in_ids)

        for student in absent_students:
            task_notify_guardian_absence.delay(student.pk, school.pk)


@shared_task(name='attendance.sweep_unclocked_out')
def task_sweep_unclocked_out():
    """
    Periodic task — runs daily at unclocked_out_alert_time (via Celery Beat).
    Finds students who checked in but were never clocked out.
    Alerts teacher and guardian.
    """
    from datetime import date
    from apps.attendance.models import StudentAttendance

    today = date.today()

    # Students who clocked in but have no clock-out time
    uncollected = StudentAttendance.objects.filter(
        date=today,
        clock_in_time__isnull=False,
        clock_out_time__isnull=True,
        status__in=['present', 'late'],
    ).select_related('student', 'school', 'branch')

    for record in uncollected:
        task_notify_unclocked_out.delay(record.pk)