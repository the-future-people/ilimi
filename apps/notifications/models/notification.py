from django.db import models
from apps.accounts.models import User
from apps.tenants.models import School


class Notification(models.Model):

    TYPE_REPORT_SUBMITTED = 'report_submitted'
    TYPE_REPORT_APPROVED = 'report_approved'
    TYPE_REPORT_RELEASED = 'report_released'
    TYPE_GENERAL = 'general'

    TYPE_CHOICES = [
        (TYPE_REPORT_SUBMITTED, 'Report Submitted'),
        (TYPE_REPORT_APPROVED, 'Report Approved'),
        (TYPE_REPORT_RELEASED, 'Report Released'),
        (TYPE_GENERAL, 'General'),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='notifications')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default=TYPE_GENERAL)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient} — {self.title}"