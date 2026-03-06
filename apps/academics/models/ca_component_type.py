from django.db import models


class CAComponentType(models.Model):
    school      = models.ForeignKey('tenants.School', on_delete=models.CASCADE, related_name='ca_component_types')
    name        = models.CharField(max_length=100)  # e.g. "Class Test", "Quiz", "Homework"
    weight      = models.DecimalField(max_digits=5, decimal_places=2)  # % of the 30 class score
    is_active   = models.BooleanField(default=True)
    is_default  = models.BooleanField(default=False)  # pre-created on school onboarding
    order       = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        unique_together = ('school', 'name')

    def __str__(self):
        return f"{self.name} ({self.weight}%)"