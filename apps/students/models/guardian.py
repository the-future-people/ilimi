from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Guardian(models.Model):

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
        ('other', 'Other'),
    ]

    # ── Platform user linkage (optional — for parent portal) ──────────
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='guardian_profile'
    )

    # ── Personal details ──────────────────────────────────────────────
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    occupation = models.CharField(max_length=200, blank=True)
    employer = models.CharField(max_length=200, blank=True)
    nationality = models.CharField(max_length=100, blank=True, default='Ghanaian')

    # ── Contact ───────────────────────────────────────────────────────
    phone = models.CharField(max_length=20)
    whatsapp_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    residential_address = models.TextField(blank=True)

    # ── Fee responsibility ────────────────────────────────────────────
    is_fee_payer = models.BooleanField(
        default=False,
        help_text="Is this guardian responsible for paying school fees?"
    )

    # ── Timestamps ────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.full_name} ({self.get_relationship_display()})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class StudentGuardian(models.Model):
    """
    Junction model linking students to their guardians.
    A student can have multiple guardians.
    A guardian can be linked to multiple students (siblings).
    """
    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE,
        related_name='student_guardians'
    )
    guardian = models.ForeignKey(
        Guardian, on_delete=models.CASCADE,
        related_name='student_guardians'
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary contact for this student"
    )

    class Meta:
        unique_together = ('student', 'guardian')

    def __str__(self):
        return f"{self.guardian.full_name} → {self.student.full_name}"

    def save(self, *args, **kwargs):
        # Only one primary guardian per student
        if self.is_primary:
            StudentGuardian.objects.filter(
                student=self.student, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)