from django.db import models
from django.utils import timezone
from apps.tenants.models import School, Branch, SchoolMember
from apps.academics.models import ClassRoom, Term


class AttendanceRegister(models.Model):
    """
    Tracks whether a class register has been submitted for a given date.
    One register per classroom per day per term.
    Once submitted, it is locked — individual StudentAttendance records
    are also locked at that point.
    """

    SESSION_CHOICES = [
        ('morning', 'Morning'),
    ]

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name='attendance_registers'
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='attendance_registers'
    )
    classroom = models.ForeignKey(
        ClassRoom, on_delete=models.CASCADE, related_name='attendance_registers'
    )
    term = models.ForeignKey(
        Term, on_delete=models.CASCADE, related_name='attendance_registers'
    )

    date = models.DateField(default=timezone.localdate)
    session = models.CharField(
        max_length=10, choices=SESSION_CHOICES, default='morning'
    )

    submitted = models.BooleanField(default=False)
    submitted_by = models.ForeignKey(
        SchoolMember, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='registers_submitted'
    )
    submitted_at = models.DateTimeField(null=True, blank=True)

    total_present = models.PositiveIntegerField(default=0)
    total_absent = models.PositiveIntegerField(default=0)
    total_late = models.PositiveIntegerField(default=0)
    total_excused = models.PositiveIntegerField(default=0)

    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['classroom', 'date', 'term', 'session']
        ordering = ['-date', 'classroom__section_name']
        verbose_name = 'Attendance Register'
        verbose_name_plural = 'Attendance Registers'

    def __str__(self):
        return f"{self.classroom} — {self.date} ({self.get_session_display()})"

    @property
    def is_submitted(self):
        return self.submitted

    @property
    def total_students(self):
        return self.total_present + self.total_absent + self.total_late + self.total_excused