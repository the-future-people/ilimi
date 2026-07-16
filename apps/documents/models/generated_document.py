from django.db import models


class GeneratedDocument(models.Model):
    school = models.ForeignKey(
        'tenants.School',
        on_delete=models.CASCADE,
        related_name='generated_documents',
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='generated_documents',
    )
    template = models.ForeignKey(
        'documents.DocumentTemplate',
        on_delete=models.PROTECT,
        related_name='generated_documents',
    )
    generated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='documents_generated',
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    merged_content = models.TextField(
        help_text="Final rendered HTML at time of generation — frozen, not re-rendered live."
    )
    pdf_file = models.FileField(upload_to='generated_documents/%Y/%m/')
    context_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text="Raw data used to fill placeholders, kept for audit/debug.",
    )

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return f"{self.template.name} — {self.student} ({self.generated_at:%Y-%m-%d})"