from django.db import models


class StaffEmergencyContact(models.Model):
    RELATIONSHIP_CHOICES = [
        ('spouse', 'Spouse'),
        ('parent', 'Parent'),
        ('sibling', 'Sibling'),
        ('child', 'Child'),
        ('relative', 'Other Relative'),
        ('friend', 'Friend'),
        ('other', 'Other'),
    ]

    staff = models.ForeignKey(
        'teachers.StaffProfile', on_delete=models.CASCADE,
        related_name='emergency_contacts'
    )
    full_name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=15, choices=RELATIONSHIP_CHOICES)
    phone = models.CharField(max_length=20)
    whatsapp_number = models.CharField(max_length=20, blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_primary', 'full_name']

    def __str__(self):
        return f"{self.full_name} ({self.get_relationship_display()})"