from django.db import models


class EmergencyContact(models.Model):

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
        ('family_friend', 'Family Friend'),
        ('other', 'Other'),
    ]

    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE,
        related_name='emergency_contacts'
    )
    full_name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    phone = models.CharField(max_length=20)
    whatsapp_number = models.CharField(max_length=20, blank=True)
    is_primary = models.BooleanField(
        default=False,
        help_text="Call this person first in an emergency"
    )

    class Meta:
        ordering = ['-is_primary', 'full_name']

    def __str__(self):
        return f"{self.full_name} ({self.get_relationship_display()}) — {self.student.full_name}"

    def save(self, *args, **kwargs):
        # Only one primary emergency contact per student
        if self.is_primary:
            EmergencyContact.objects.filter(
                student=self.student, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)