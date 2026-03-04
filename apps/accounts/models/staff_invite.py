import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta


def invite_expiry():
    return timezone.now() + timedelta(hours=48)


class StaffPortalInvite(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    ]

    staff = models.OneToOneField(
        'teachers.StaffProfile',
        on_delete=models.CASCADE,
        related_name='portal_invite'
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=invite_expiry)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    invited_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='staff_invites_sent'
    )

    class Meta:
        verbose_name = 'Staff Portal Invite'
        verbose_name_plural = 'Staff Portal Invites'

    def __str__(self):
        return f"Invite for {self.staff.full_name} ({self.status})"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return self.status == 'pending' and not self.is_expired