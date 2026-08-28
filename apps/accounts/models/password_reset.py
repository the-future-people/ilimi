import secrets
from datetime import timedelta

from django.db import models
from django.utils import timezone

MAX_ATTEMPTS = 5


def code_expiry():
    return timezone.now() + timedelta(minutes=10)


def ticket_expiry():
    return timezone.now() + timedelta(minutes=15)


class PasswordResetOTP(models.Model):
    """
    A single password reset attempt, proved by holding the phone.

    Kept separate from PendingRegistration, which carries school
    registration fields that mean nothing here.
    """

    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='password_resets',
    )
    code = models.CharField(max_length=6)
    expires_at = models.DateTimeField(default=code_expiry)
    attempts = models.PositiveSmallIntegerField(default=0)

    # Issued once the code is verified, so a weak new password can be
    # corrected without burning the code and sending another SMS.
    ticket = models.CharField(max_length=64, blank=True, db_index=True)
    ticket_expires_at = models.DateTimeField(null=True, blank=True)

    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Password reset for {self.user_id}'

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_exhausted(self):
        return self.attempts >= MAX_ATTEMPTS

    @property
    def is_usable(self):
        return not (self.used_at or self.is_expired or self.is_exhausted)

    def issue_ticket(self):
        self.ticket = secrets.token_urlsafe(32)
        self.ticket_expires_at = ticket_expiry()
        self.save(update_fields=['ticket', 'ticket_expires_at'])
        return self.ticket

    @property
    def ticket_is_valid(self):
        if not self.ticket or self.used_at:
            return False
        return bool(self.ticket_expires_at and timezone.now() <= self.ticket_expires_at)