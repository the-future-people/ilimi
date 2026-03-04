from django.db import models
from apps.tenants.models import School, Branch


class AttendanceSettings(models.Model):
    """
    Per-school (or per-branch) attendance configuration.
    Branch-level settings override school-wide settings.
    """

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name='attendance_settings'
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='attendance_settings',
        help_text="Leave blank for school-wide settings."
    )

    # Timing
    school_start_time = models.TimeField(default='07:30')
    late_grace_minutes = models.PositiveIntegerField(default=15)
    school_close_time = models.TimeField(default='15:00')
    unclocked_out_alert_time = models.TimeField(
        default='15:30',
        help_text="Time to alert teacher and guardian for students not yet clocked out."
    )

    # Fingerprint
    allow_fingerprint_exit = models.BooleanField(default=False)

    # SMS triggers
    sms_on_checkin = models.BooleanField(default=True)
    sms_on_checkout = models.BooleanField(default=True)
    sms_on_late_arrival = models.BooleanField(default=True)
    sms_on_absence = models.BooleanField(default=True)
    absence_notify_time = models.TimeField(
        default='09:00',
        help_text="Time to send absence SMS for students who have not checked in."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['school', 'branch']
        verbose_name = 'Attendance Settings'
        verbose_name_plural = 'Attendance Settings'

    def __str__(self):
        if self.branch:
            return f"Attendance Settings - {self.school.name} / {self.branch.name}"
        return f"Attendance Settings - {self.school.name} (School-wide)"

    @property
    def late_cutoff_display(self):
        from datetime import datetime, timedelta
        start = datetime.combine(datetime.today(), self.school_start_time)
        cutoff = start + timedelta(minutes=self.late_grace_minutes)
        return cutoff.time().strftime('%H:%M')