from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

def guardian_photo_path(instance, filename):
    ext = filename.split('.')[-1]
    return f"guardians/{instance.pk}/photo.{ext}"


def guardian_fingerprint_path(instance, filename):
    ext = filename.split('.')[-1]
    return f"guardians/{instance.pk}/fingerprint.{ext}"


def guardian_document_path(instance, filename):
    ext = filename.split('.')[-1]
    return f"guardians/{instance.pk}/documents/{filename}"

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

    TITLE_CHOICES = [
        ('mr', 'Mr.'),
        ('mrs', 'Mrs.'),
        ('miss', 'Miss'),
        ('dr', 'Dr.'),
        ('prof', 'Prof.'),
        ('rev', 'Rev.'),
        ('pastor', 'Pastor'),
        ('alhaji', 'Alhaji'),
        ('hajia', 'Hajia'),
        ('hon', 'Hon.'),
        ('other', 'Other'),
    ]

    # ── Platform user linkage (optional — for parent portal) ──────────
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='guardian_profile'
    )

    # ── Personal details ──────────────────────────────────────────
    title = models.CharField(max_length=10, choices=TITLE_CHOICES, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    occupation = models.ForeignKey(
        'core.Occupation', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='guardians'
    )
    employer = models.CharField(max_length=200, blank=True)
    nationality = models.CharField(max_length=100, blank=True, default='Ghanaian')

    # ── Contact ──────────────────────────────────────────────────────
    phone = models.CharField(max_length=20)
    whatsapp_number = models.CharField(max_length=20, blank=True)
    secondary_phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    residential_address = models.TextField(blank=True)
    digital_address = models.CharField(max_length=20, blank=True)

    # ── Identity documents ──────────────────────────────────────────
    ghana_card_number = models.CharField(max_length=20, blank=True)
    ghana_card_front = models.ImageField(upload_to=guardian_document_path, null=True, blank=True)
    ghana_card_back = models.ImageField(upload_to=guardian_document_path, null=True, blank=True)

    # ── Biometrics ──────────────────────────────────────────────────
    photo = models.ImageField(upload_to=guardian_photo_path, null=True, blank=True)
    fingerprint_data = models.FileField(upload_to=guardian_fingerprint_path, null=True, blank=True)

    # ── Pickup authorization ─────────────────────────────────────────
    can_pickup = models.BooleanField(default=True, help_text="Authorized to pick up the student")

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