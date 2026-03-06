from django.db import models


class CAScore(models.Model):

    GRADE_CHOICES = [
        ('A1', 'A1'), ('B2', 'B2'), ('B3', 'B3'),
        ('C4', 'C4'), ('C5', 'C5'), ('C6', 'C6'),
        ('D7', 'D7'), ('E8', 'E8'), ('F9', 'F9'),
    ]

    school      = models.ForeignKey('tenants.School', on_delete=models.CASCADE, related_name='ca_scores')
    branch      = models.ForeignKey('tenants.Branch', on_delete=models.SET_NULL, null=True, blank=True)
    student     = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='ca_scores')
    classroom   = models.ForeignKey('academics.ClassRoom', on_delete=models.CASCADE, related_name='ca_scores')
    subject     = models.ForeignKey('academics.Subject', on_delete=models.CASCADE, related_name='ca_scores')
    term        = models.ForeignKey('academics.Term', on_delete=models.CASCADE, related_name='ca_scores')

    class_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)   # computed from components, max 30
    exam_score  = models.DecimalField(max_digits=5, decimal_places=2, default=0)   # manually entered, max 70

    total       = models.DecimalField(max_digits=5, decimal_places=2, default=0)   # computed
    grade       = models.CharField(max_length=2, choices=GRADE_CHOICES, blank=True)

    submitted    = models.BooleanField(default=False)
    submitted_by = models.ForeignKey('tenants.SchoolMember', on_delete=models.SET_NULL, null=True, blank=True, related_name='ca_submissions')
    submitted_at = models.DateTimeField(null=True, blank=True)
    locked       = models.BooleanField(default=False)

    remarks      = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'subject', 'term')
        ordering = ['student__last_name', 'student__first_name']

    def __str__(self):
        return f"{self.student} — {self.subject} — {self.term} — {self.total}"

    @staticmethod
    def compute_grade(total):
        if total >= 80: return 'A1'
        if total >= 70: return 'B2'
        if total >= 60: return 'B3'
        if total >= 55: return 'C4'
        if total >= 50: return 'C5'
        if total >= 45: return 'C6'
        if total >= 40: return 'D7'
        if total >= 30: return 'E8'
        return 'F9'

    def save(self, *args, **kwargs):
        self.total = self.class_score + self.exam_score
        self.grade = self.compute_grade(float(self.total))
        super().save(*args, **kwargs)