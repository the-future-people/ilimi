from django.db import models


class CAComponent(models.Model):
    school          = models.ForeignKey('tenants.School', on_delete=models.CASCADE, related_name='ca_components')
    branch          = models.ForeignKey('tenants.Branch', on_delete=models.SET_NULL, null=True, blank=True)
    classroom       = models.ForeignKey('academics.ClassRoom', on_delete=models.CASCADE, related_name='ca_components')
    subject         = models.ForeignKey('academics.Subject', on_delete=models.CASCADE, related_name='ca_components')
    term            = models.ForeignKey('academics.Term', on_delete=models.CASCADE, related_name='ca_components')
    component_type  = models.ForeignKey('academics.CAComponentType', on_delete=models.CASCADE, related_name='components')

    name            = models.CharField(max_length=100)  # e.g. "Class Test 1", "Quiz 2"
    max_score       = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    date            = models.DateField()
    created_by      = models.ForeignKey('tenants.SchoolMember', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_ca_components')

    class Meta:
        ordering = ['date', 'name']
        unique_together = ('classroom', 'subject', 'term', 'name')

    def __str__(self):
        return f"{self.name} — {self.subject} — {self.classroom}"