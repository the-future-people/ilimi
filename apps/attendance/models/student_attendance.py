from django.db import models
from django.utils import timezone
from apps.tenants.models import School, Branch
from apps.academics.models import Term
from apps.students.models import Student
from apps.tenants.models import SchoolMember


class StudentAttendance(models.Model):

    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    ]

    SOURCE_CHOICES = [
        ('fingerprint', 'Fingerprint Device'),
        ('manual', 'Manual Entry'),
        ('system', 'System Generated'),
    ]

    # Linkage
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name='student_attendances'
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='student_attendances'
    )
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='attendances'
    )
    term = models.ForeignKey(
        Term, on_delete=models.CASCADE, related_name='student_attendances'
    )
    marked_by = models.ForeignKey(
        SchoolMember, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='attendance_marked',
        help_text="Staff member who marked this attendance record."
    )

    # Attendance Data
    date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='absent')
    source = models.CharField(
        max_length=15, choices=SOURCE_CHOICES, default='manual',
        help_text="How this record was created."
    )
    locked = models.BooleanField(
        default=False,
        help_text="Fingerprint records are locked. Editing requires admin + override reason."
    )

    # Clock In
    clock_in_time = models.TimeField(null=True, blank=True)
    via_fingerprint = models.BooleanField(default=False)

    # Clock Out / Pickup
    clock_out_time = models.TimeField(null=True, blank=True)
    clock_out_via_fingerprint = models.BooleanField(default=False)
    early_dismissal = models.BooleanField(default=False)
    early_dismissal_reason = models.TextField(blank=True)
    picked_up_by = models.ForeignKey(
        'attendance.AuthorisedPickup',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pickups'
    )
    pickup_verified_by = models.ForeignKey(
        SchoolMember, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pickups_verified'
    )

    # Guardian Notification
    guardian_notified = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)

    # Override Audit
    override_reason = models.TextField(blank=True)
    override_by = models.ForeignKey(
        SchoolMember, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='attendance_overrides'
    )

    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', 'student__last_name']
        unique_together = ['student', 'date', 'term']
        verbose_name = 'Student Attendance'
        verbose_name_plural = 'Student Attendance Records'

    def __str__(self):
        return f"{self.student.full_name} - {self.date} - {self.get_status_display()}"

    @property
    def is_clocked_out(self):
        return self.clock_out_time is not None

    @property
    def needs_pickup_alert(self):
        return self.clock_in_time is not None and self.clock_out_time is None