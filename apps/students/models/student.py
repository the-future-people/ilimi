import os
from django.db import models
from django.utils import timezone
from apps.tenants.models import School, Branch
from apps.academics.models import ClassRoom


def student_photo_path(instance, filename):
    ext = filename.split('.')[-1]
    return f"students/{instance.school.id}/photos/{instance.student_id}.{ext}"


def student_fingerprint_path(instance, filename):
    ext = filename.split('.')[-1]
    return f"students/{instance.school.id}/fingerprints/{instance.student_id}.{ext}"


class Student(models.Model):

    # ── Status choices ────────────────────────────────────────────────
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('graduated', 'Graduated'),
        ('withdrawn', 'Withdrawn'),
        ('suspended', 'Suspended'),
        ('deceased', 'Deceased'),
    ]

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    RELIGION_CHOICES = [
        ('christian', 'Christian'),
        ('muslim', 'Muslim'),
        ('traditionalist', 'Traditionalist'),
        ('other', 'Other'),
        ('none', 'None / Prefer not to say'),
    ]

    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
        ('unknown', 'Unknown'),
    ]

    BOARDING_STATUS_CHOICES = [
        ('day', 'Day Student'),
        ('boarder', 'Full Boarder'),
        ('weekly', 'Weekly Boarder'),
    ]

    GHANA_REGIONS = [
        ('greater_accra', 'Greater Accra'),
        ('ashanti', 'Ashanti'),
        ('western', 'Western'),
        ('western_north', 'Western North'),
        ('central', 'Central'),
        ('eastern', 'Eastern'),
        ('volta', 'Volta'),
        ('oti', 'Oti'),
        ('northern', 'Northern'),
        ('savannah', 'Savannah'),
        ('north_east', 'North East'),
        ('upper_east', 'Upper East'),
        ('upper_west', 'Upper West'),
        ('bono', 'Bono'),
        ('bono_east', 'Bono East'),
        ('ahafo', 'Ahafo'),
        ('other', 'Other / Outside Ghana'),
    ]

    # ── School linkage ────────────────────────────────────────────────
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name='students'
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='students'
    )
    current_class = models.ForeignKey(
        ClassRoom, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='students'
    )

    # ── Identity ──────────────────────────────────────────────────────
    student_id = models.CharField(max_length=30, unique=True, blank=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    place_of_birth = models.CharField(max_length=200, blank=True)
    home_town = models.CharField(max_length=200, blank=True)
    nationality = models.CharField(max_length=100, default='Ghanaian')
    mother_tongue = models.CharField(max_length=100, blank=True)

    # ── Official documents ────────────────────────────────────────────
    birth_certificate_number = models.CharField(max_length=100, blank=True)
    nhis_number = models.CharField(
        max_length=50, blank=True,
        verbose_name='NHIS Card Number'
    )

    # ── Contact/Address ───────────────────────────────────────────────
    residential_address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField(
        max_length=30, choices=GHANA_REGIONS, blank=True
    )

    # ── Religion ─────────────────────────────────────────────────────
    religion = models.CharField(
        max_length=20, choices=RELIGION_CHOICES, blank=True
    )

    # ── Health ────────────────────────────────────────────────────────
    blood_group = models.CharField(
        max_length=10, choices=BLOOD_GROUP_CHOICES, default='unknown'
    )
    known_allergies = models.TextField(blank=True)
    medical_notes = models.TextField(blank=True)
    disability_status = models.BooleanField(default=False)
    disability_description = models.TextField(blank=True)

    # ── Academic ──────────────────────────────────────────────────────
    enrollment_date = models.DateField(default=timezone.localdate)
    expected_graduation_year = models.PositiveIntegerField(null=True, blank=True)
    previous_school = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default='active'
    )
    withdrawal_reason = models.TextField(blank=True)

    # ── Boarding ──────────────────────────────────────────────────────
    boarding_status = models.CharField(
        max_length=10, choices=BOARDING_STATUS_CHOICES, default='day'
    )
    house_dormitory = models.CharField(max_length=100, blank=True)
    bus_route = models.CharField(max_length=100, blank=True)
    locker_number = models.CharField(max_length=20, blank=True)

    # ── Talents & extra ───────────────────────────────────────────────
    talents_skills = models.TextField(blank=True)
    additional_notes = models.TextField(blank=True)

    # ── Biometrics ────────────────────────────────────────────────────
    photo = models.ImageField(
        upload_to=student_photo_path, null=True, blank=True
    )
    fingerprint_data = models.FileField(
        upload_to=student_fingerprint_path, null=True, blank=True
    )

    # ── Siblings ─────────────────────────────────────────────────────
    siblings = models.ManyToManyField(
        'self', blank=True, symmetrical=True,
        related_name='sibling_of'
    )

    # ── Timestamps ───────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.full_name} ({self.student_id})"

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(p for p in parts if p)

    def save(self, *args, **kwargs):
        if not self.student_id:
            self.student_id = self._generate_student_id()
        super().save(*args, **kwargs)

    def _generate_student_id(self):
        # Format: SCH_INITIALS/YEAR/SEQUENCE e.g. ITA/2026/0001
        initials = ''.join(
            word[0].upper()
            for word in self.school.name.split()[:3]
        )
        year = timezone.now().year
        last = Student.objects.filter(
            school=self.school
        ).order_by('-created_at').first()
        if last and last.student_id:
            try:
                seq = int(last.student_id.split('/')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{initials}/{year}/{seq:04d}"