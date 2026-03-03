from django.db import models
from apps.tenants.models import School
from apps.students.models import Student
from apps.tenants.models import SchoolMember


class AuthorisedPickup(models.Model):

    RELATIONSHIP_CHOICES = [
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('uncle', 'Uncle'),
        ('aunt', 'Aunt'),
        ('grandfather', 'Grandfather'),
        ('grandmother', 'Grandmother'),
        ('brother', 'Brother'),
        ('sister', 'Sister'),
        ('guardian', 'Legal Guardian'),
        ('driver', 'Driver'),
        ('family_friend', 'Family Friend'),
        ('other', 'Other'),
    ]

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name='authorised_pickups'
    )
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='authorised_pickups'
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    phone = models.CharField(max_length=20)
    ghana_card_number = models.CharField(max_length=50, blank=True)
    photo = models.ImageField(
        upload_to='authorised_pickups/', null=True, blank=True,
        help_text="Photo for visual verification by gate staff."
    )
    is_active = models.BooleanField(default=True)
    added_by = models.ForeignKey(
        SchoolMember, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='authorised_pickups_added'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['student__last_name', 'last_name']
        verbose_name = 'Authorised Pickup Person'
        verbose_name_plural = 'Authorised Pickup Persons'

    def __str__(self):
        return (
            f"{self.full_name} ({self.get_relationship_display()}) "
            f"- {self.student.full_name}"
        )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"