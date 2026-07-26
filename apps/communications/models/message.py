from django.db import models


class Message(models.Model):
    """
    A single composed communication — SMS only for v1 (email/WhatsApp
    bulk-send don't exist yet; the existing WhatsApp link-share and
    consent-PDF-email flows are unrelated, per-record features, not a
    broadcast channel).

    Two paths into 'sent': an admin composing goes straight from draft to
    approved+sent in one action. A registrar composing lands in
    pending_approval and waits — mirrors the PaymentReminderRequest pattern
    from apps.notifications, generalized across any sender/audience rather
    than tied to one fee reminder.
    """

    AUDIENCE_CHOICES = [
        ('single_guardian', 'Single Guardian'),
        ('single_staff', 'Single Staff Member'),
        ('class_guardians', "A Class's Guardians"),
        ('all_staff', 'All Staff'),
        ('all_guardians', 'All Guardians (Broadcast)'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('sent', 'Sent'),
        ('declined', 'Declined'),
        ('failed', 'Failed'),
    ]

    school = models.ForeignKey(
        'tenants.School', on_delete=models.CASCADE, related_name='messages'
    )
    composed_by = models.ForeignKey(
        'tenants.SchoolMember', on_delete=models.CASCADE,
        related_name='messages_composed'
    )

    title = models.CharField(
        max_length=150,
        help_text="Internal label for this message — not sent to recipients."
    )
    body = models.TextField(
        help_text="The actual SMS text. Links (e.g. an enrolment invite URL) "
                   "can be included directly in this text."
    )

    audience_type = models.CharField(max_length=20, choices=AUDIENCE_CHOICES)
    # Exactly one of these is set, depending on audience_type — enforced in
    # the service layer, not the DB, since the right one varies by type.
    target_student = models.ForeignKey(
        'students.Student', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='messages_targeted',
        help_text="Set when audience_type='single_guardian' — message goes "
                   "to this student's primary guardian."
    )
    target_staff_member = models.ForeignKey(
        'tenants.SchoolMember', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='messages_received_as_target',
        help_text="Set when audience_type='single_staff'."
    )
    target_classroom = models.ForeignKey(
        'academics.ClassRoom', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='messages_targeted',
        help_text="Set when audience_type='class_guardians'."
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    reviewed_by = models.ForeignKey(
        'tenants.SchoolMember', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='messages_reviewed',
        help_text="Who approved or declined — null if composed_by is already "
                   "admin-tier and it went straight through."
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    decline_reason = models.CharField(max_length=255, blank=True)

    recipient_count = models.PositiveIntegerField(
        default=0,
        help_text="How many distinct phone numbers this actually reached, "
                   "filled in at send time after audience resolution + dedup."
    )
    sent_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"