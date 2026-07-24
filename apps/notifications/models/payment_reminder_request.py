from django.db import models


class PaymentReminderRequest(models.Model):
    """
    An accountant's request that an admin send a payment-reminder SMS to a
    guardian. Accountants cannot message parents directly — Communications
    stays admin-only (see apps/tenants/permissions.py). This is the
    narrow, real channel for a lower-tier role to flag that a nudge is
    needed, without touching the actual send path.

    Mirrors the DemoRequest pattern in apps/agamotto — someone without
    send-access creates a request, someone with authority acts on it.
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved — sent'),
        ('declined', 'Declined'),
    ]

    school = models.ForeignKey(
        'tenants.School', on_delete=models.CASCADE,
        related_name='payment_reminder_requests'
    )
    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE,
        related_name='payment_reminder_requests'
    )
    student_fee = models.ForeignKey(
        'fees.StudentFee', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reminder_requests',
        help_text="The specific fee this reminder concerns, if any."
    )

    requested_by = models.ForeignKey(
        'tenants.SchoolMember', on_delete=models.CASCADE,
        related_name='payment_reminders_requested'
    )
    note = models.TextField(
        blank=True,
        help_text="Optional context from the requester — e.g. 'third "
                   "reminder, please call rather than SMS'."
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        'tenants.SchoolMember', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='payment_reminders_reviewed'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    decline_reason = models.CharField(max_length=255, blank=True)

    message_sent = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Payment Reminder Request"
        verbose_name_plural = "Payment Reminder Requests"

    def __str__(self):
        return f"Reminder for {self.student.full_name} ({self.get_status_display()})"