from django.db import models


class Excursion(models.Model):
    school = models.ForeignKey(
        'tenants.School', on_delete=models.CASCADE, related_name='excursions'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    date = models.DateField()
    classrooms = models.ManyToManyField(
        'academics.ClassRoom', related_name='excursions', blank=True
    )
    created_by = models.ForeignKey(
        'tenants.SchoolMember', on_delete=models.SET_NULL,
        null=True, related_name='created_excursions'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.name} ({self.date})"