from django.db import models


class DocumentTemplate(models.Model):
    DOCUMENT_TYPES = [
        ('recommendation_letter', 'Recommendation Letter'),
        ('introduction_letter', 'Introduction Letter'),
        ('transcript', 'Transcript'),
        ('transfer_letter', 'Transfer Letter'),
        ('financial_clearance', 'Financial Clearance'),
        ('custom', 'Custom'),
    ]

    school = models.ForeignKey(
        'tenants.School',
        on_delete=models.CASCADE,
        related_name='document_templates',
    )
    name = models.CharField(max_length=255)
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES)
    body_html = models.TextField(
        help_text="HTML with {{placeholder}} tokens. For computed docs, this is the wrapper/letterhead containing {{computed_content}}."
    )
    extra_fields = models.JSONField(
        default=list,
        blank=True,
        help_text="Admin-fillable fields at generation time, e.g. "
                   "[{'token': 'embassy_name', 'label': 'Embassy Name', 'type': 'text', 'required': True}]",
    )
    requires_signature = models.BooleanField(default=True)
    is_computed = models.BooleanField(
        default=False,
        help_text="True for Transcript-style docs assembled from real data, not free text.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.school.name})"