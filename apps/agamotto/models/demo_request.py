from django.db import models


class DemoRequest(models.Model):
    """
    A lead from the public marketing site: someone asking for a demo or
    leaving their details for follow-up.

    The first and (for now) only piece of Agamotto — the lead-pipeline
    corner of a platform that will grow into Ilimi's internal intelligence
    layer. See apps/agamotto/README.md.
    """

    STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('converted', 'Converted'),
        ('closed', 'Closed'),
    ]

    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    school_name = models.CharField(
        max_length=200, blank=True,
        help_text="Optional — helps us prepare for the demo."
    )
    message = models.TextField(
        blank=True,
        help_text="Optional — anything they told us about their school."
    )

    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default='new',
        help_text="Follow-up state. We promise a reply within 2 hours."
    )
    source = models.CharField(
        max_length=50, default='landing_page',
        help_text="Where the lead came from, for future channels."
    )

    # Light context for spam triage / future analysis. Low sensitivity.
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Demo Request"
        verbose_name_plural = "Demo Requests"

    def __str__(self):
        who = self.school_name or self.name
        return f"{who} ({self.get_status_display()})"