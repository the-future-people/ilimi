from django.db import models
from apps.accounts.models import User


class ReportCardRemark(models.Model):
    report_card = models.OneToOneField(
        'reports.ReportCard',
        on_delete=models.CASCADE,
        related_name='remark'
    )
    teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='report_card_remarks'
    )
    remark = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Remark — {self.report_card.student} — {self.report_card.term}"