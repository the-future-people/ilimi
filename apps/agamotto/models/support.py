from datetime import timedelta

from django.db import models
from django.utils import timezone

SESSION_HOURS = 24


def session_expiry():
    return timezone.now() + timedelta(hours=SESSION_HOURS)


class SupportSession(models.Model):
    """
    A window in which Ilimi staff may read one school's data.

    Ilimi holds no standing access to a school's records. Support work
    happens inside a session that states why it was opened, expires on its
    own, records every request made while it is open, and sends the school
    a readable summary when it closes.
    """

    school = models.ForeignKey(
        'tenants.School',
        on_delete=models.CASCADE,
        related_name='support_sessions',
    )
    opened_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='support_sessions',
    )
    reason = models.TextField(
        help_text='Why this session was opened. Shown to the school in the summary.',
    )

    opened_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=session_expiry)
    closed_at = models.DateTimeField(null=True, blank=True)

    summary_sent_at = models.DateTimeField(null=True, blank=True)
    summary_sent_to = models.EmailField(blank=True)

    class Meta:
        ordering = ['-opened_at']
        indexes = [
            models.Index(fields=['school', 'closed_at']),
        ]

    def __str__(self):
        return f'Support session {self.pk} on {self.school_id}'

    @property
    def is_open(self):
        return self.closed_at is None and timezone.now() <= self.expires_at

    def close(self):
        if self.closed_at is None:
            self.closed_at = timezone.now()
            self.save(update_fields=['closed_at'])


class SupportAccessLog(models.Model):
    """
    One request made during a support session.

    Everything is recorded rather than only what seems significant, so the
    record cannot be argued with. The school's summary condenses this into
    something readable; the detail stays here.
    """

    session = models.ForeignKey(
        SupportSession,
        on_delete=models.CASCADE,
        related_name='accesses',
    )
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=255)
    query = models.CharField(max_length=255, blank=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['at']
        indexes = [
            models.Index(fields=['session', 'at']),
        ]

    def __str__(self):
        return f'{self.method} {self.path}'