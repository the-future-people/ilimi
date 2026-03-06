from django.db import models


class CAComponentScore(models.Model):
    school      = models.ForeignKey('tenants.School', on_delete=models.CASCADE, related_name='ca_component_scores')
    student     = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='ca_component_scores')
    component   = models.ForeignKey('academics.CAComponent', on_delete=models.CASCADE, related_name='scores')
    score       = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    remarks     = models.TextField(blank=True)
    entered_by  = models.ForeignKey('tenants.SchoolMember', on_delete=models.SET_NULL, null=True, blank=True, related_name='entered_ca_scores')
    locked      = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'component')
        ordering = ['student__last_name', 'student__first_name']

    def __str__(self):
        return f"{self.student} — {self.component} — {self.score}"