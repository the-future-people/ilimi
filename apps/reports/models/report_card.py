from django.db import models
from apps.accounts.models import User
from apps.tenants.models import School, Branch
from apps.students.models import Student
from apps.academics.models import ClassRoom, Term, Subject


class ReportCard(models.Model):

    STATUS_DRAFT = 'draft'
    STATUS_SUBMITTED = 'submitted'
    STATUS_APPROVED = 'approved'
    STATUS_RELEASED = 'released'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_RELEASED, 'Released'),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='report_cards')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='report_cards')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='report_cards')
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name='report_cards')
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='report_cards')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    head_comment = models.TextField(blank=True, default='')

    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='generated_report_cards')
    generated_at = models.DateTimeField(auto_now_add=True)

    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_report_cards')
    approved_at = models.DateTimeField(null=True, blank=True)

    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'classroom', 'term')
        ordering = ['student__last_name', 'student__first_name']

    def __str__(self):
        return f"{self.student} — {self.classroom} — {self.term}"