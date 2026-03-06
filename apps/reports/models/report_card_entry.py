from django.db import models
from apps.academics.models import Subject


class ReportCardEntry(models.Model):
    report_card = models.ForeignKey(
        'reports.ReportCard',
        on_delete=models.CASCADE,
        related_name='entries'
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='report_entries')

    class_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    exam_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    grade = models.CharField(max_length=5, default='F9')
    remarks = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        unique_together = ('report_card', 'subject')
        ordering = ['subject__name']

    def __str__(self):
        return f"{self.report_card.student} — {self.subject.name} — {self.grade}"