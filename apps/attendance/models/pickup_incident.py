from django.db import models
from apps.tenants.models import School
from apps.students.models import Student, Guardian
from apps.tenants.models import SchoolMember


class PickupIncident(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending - Awaiting Guardian Response'),
        ('authorised', 'Authorised - Student Released'),
        ('denied', 'Denied - Student Retained'),
        ('escalated', 'Escalated - Head Teacher Notified'),
    ]

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name='pickup_incidents'
    )
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='pickup_incidents'
    )

    # The person who showed up
    attempted_by_name = models.CharField(max_length=200)
    attempted_by_phone = models.CharField(max_length=20, blank=True)
    attempted_by_id_number = models.CharField(max_length=50, blank=True)
    reason_given = models.TextField(blank=True)
    attempted_at = models.DateTimeField(auto_now_add=True)

    # Guardian authorisation flow
    guardian_notified = models.ForeignKey(
        Guardian, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pickup_incidents_notified'
    )
    authorisation_sms_sent = models.BooleanField(default=False)
    authorisation_sms_sent_at = models.DateTimeField(null=True, blank=True)
    guardian_response_at = models.DateTimeField(null=True, blank=True)

    # Resolution
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    student_released = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        SchoolMember, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pickup_incidents_resolved'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    # Escalation
    escalated = models.BooleanField(default=False)
    escalated_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-attempted_at']
        verbose_name = 'Pickup Incident'
        verbose_name_plural = 'Pickup Incidents'

    def __str__(self):
        return (
            f"Pickup Incident - {self.student.full_name} "
            f"by {self.attempted_by_name} [{self.get_status_display()}]"
        )

    @property
    def is_resolved(self):
        return self.status in ('authorised', 'denied')