from django.db import models
from django.utils import timezone
from apps.tenants.models import School, Branch
from apps.academics.models import Term
from apps.teachers.models import StaffProfile


class StaffAttendance(models.Model):

    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    ]

    SOURCE_CHOICES = [
        ('fingerprint', 'Fingerprint Device'),
        ('manual', 'Manual Entry'),
    ]

    # Linkage
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name='staff_attendances'
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='staff_attendances'
    )
    staff = models.ForeignKey(
        StaffProfile, on_delete=models.CASCADE, related_name='attendances'
    )
    term = models.ForeignKey(
        Term, on_delete=models.CASCADE, related_name='staff_attendances'
    )

    # Attendance Data
    date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='absent')
    source = models.CharField(max_length=15, choices=SOURCE_CHOICES, default='manual')
    locked = models.BooleanField(default=False)

    # Clock In / Out
    clock_in_time = models.TimeField(null=True, blank=True)
    clock_out_time = models.TimeField(null=True, blank=True)
    via_fingerprint = models.BooleanField(default=False)
    hours_worked = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True,
        help_text="Computed automatically from clock in/out times."
    )

    # Override Audit
    override_reason = models.TextField(blank=True)

    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', 'staff__last_name']
        unique_together = ['staff', 'date', 'term']
        verbose_name = 'Staff Attendance'
        verbose_name_plural = 'Staff Attendance Records'

    def __str__(self):
        return f"{self.staff.full_name} - {self.date} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        # Auto-compute hours worked on save if both times are present
        if self.clock_in_time and self.clock_out_time:
            from datetime import datetime, date
            dt_in = datetime.combine(date.today(), self.clock_in_time)
            dt_out = datetime.combine(date.today(), self.clock_out_time)
            delta = dt_out - dt_in
            if delta.total_seconds() > 0:
                self.hours_worked = round(delta.total_seconds() / 3600, 2)
        super().save(*args, **kwargs)