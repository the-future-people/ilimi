from django.db import models
from django.utils import timezone
from apps.tenants.models import School, Branch


def staff_photo_path(instance, filename):
    ext = filename.split('.')[-1]
    return f"staff/{instance.school.id}/photos/{instance.staff_id}.{ext}"


class StaffProfile(models.Model):

    # ── Employment Type ───────────────────────────────────────────────
    EMPLOYMENT_TYPE_CHOICES = [
        ('permanent', 'Permanent'),
        ('contract', 'Contract'),
        ('part_time', 'Part Time'),
        ('national_service', 'National Service'),
        ('volunteer', 'Volunteer'),
    ]

    # ── Gender ────────────────────────────────────────────────────────
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    # ── Marital Status ────────────────────────────────────────────────
    MARITAL_STATUS_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ]

    # ── Highest Qualification ─────────────────────────────────────────
    QUALIFICATION_CHOICES = [
        ('wassce', 'WASSCE'),
        ('diploma', 'Diploma'),
        ('bachelors', "Bachelor's Degree"),
        ('pgde', 'PGDE'),
        ('masters', "Master's Degree"),
        ('phd', 'PhD'),
        ('other', 'Other'),
    ]

    # ── Employment Status ─────────────────────────────────────────────
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('on_leave', 'On Leave'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
        ('resigned', 'Resigned'),
        ('retired', 'Retired'),
        ('deceased', 'Deceased'),
    ]

    # ── Ghana Regions ─────────────────────────────────────────────────
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

    # ── Bank Choices ──────────────────────────────────────────────────
    BANK_CHOICES = [
        ('gcb', 'GCB Bank'),
        ('ecobank', 'Ecobank'),
        ('absa', 'Absa Bank'),
        ('stanbic', 'Stanbic Bank'),
        ('zenith', 'Zenith Bank'),
        ('uba', 'UBA Ghana'),
        ('fidelity', 'Fidelity Bank'),
        ('calbank', 'CalBank'),
        ('agricultural', 'Agricultural Development Bank'),
        ('prudential', 'Prudential Bank'),
        ('republic', 'Republic Bank'),
        ('societe', 'Societe Generale'),
        ('access', 'Access Bank'),
        ('other', 'Other'),
    ]

    # ── School linkage ────────────────────────────────────────────────
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name='staff'
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='staff'
    )
    user = models.OneToOneField(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='staff_profile'
    )

    # ── Identity ──────────────────────────────────────────────────────
    staff_id = models.CharField(max_length=30, unique=True, blank=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    nationality = models.CharField(max_length=100, default='Ghanaian')
    marital_status = models.CharField(
        max_length=10, choices=MARITAL_STATUS_CHOICES, blank=True
    )
    number_of_dependants = models.PositiveIntegerField(default=0)
    photo = models.ImageField(
        upload_to=staff_photo_path, null=True, blank=True
    )

    # ── Contact ───────────────────────────────────────────────────────
    phone = models.CharField(max_length=20)
    whatsapp_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    residential_address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=30, choices=GHANA_REGIONS, blank=True)

    # ── Official Documents ────────────────────────────────────────────
    ghana_card_number = models.CharField(max_length=50, blank=True)
    ssnit_number = models.CharField(
        max_length=50, blank=True, verbose_name='SSNIT Number'
    )
    ntc_license_number = models.CharField(
        max_length=50, blank=True, verbose_name='NTC License Number'
    )

    # ── Qualifications ────────────────────────────────────────────────
    highest_qualification = models.CharField(
        max_length=20, choices=QUALIFICATION_CHOICES, blank=True
    )
    institution_attended = models.CharField(max_length=255, blank=True)
    years_of_experience = models.PositiveIntegerField(default=0)

    # ── Subject Specializations ───────────────────────────────────────
    subject_specializations = models.ManyToManyField(
        'academics.Subject',
        blank=True,
        related_name='specialist_staff',
    )

    # ── Employment ────────────────────────────────────────────────────
    employment_type = models.CharField(
        max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, default='permanent'
    )
    salary_grade = models.CharField(max_length=50, blank=True)
    date_of_first_appointment = models.DateField(null=True, blank=True)
    date_joined_school = models.DateField(null=True, blank=True)
    is_on_probation = models.BooleanField(default=False)
    probation_end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default='active'
    )
    termination_date = models.DateField(null=True, blank=True)
    termination_reason = models.TextField(blank=True)
    is_head_of_department = models.BooleanField(default=False)

    # ── Leave ─────────────────────────────────────────────────────────
    leave_entitlement_days = models.PositiveIntegerField(default=21)
    leave_days_taken = models.PositiveIntegerField(default=0)

    # ── Banking ───────────────────────────────────────────────────────
    bank_name = models.CharField(max_length=20, choices=BANK_CHOICES, blank=True)
    bank_branch = models.CharField(max_length=200, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    momo_number = models.CharField(
        max_length=20, blank=True, verbose_name='MoMo Number'
    )

    # ── Next of Kin ───────────────────────────────────────────────────
    next_of_kin_name = models.CharField(max_length=200, blank=True)
    next_of_kin_relationship = models.CharField(max_length=100, blank=True)
    next_of_kin_phone = models.CharField(max_length=20, blank=True)
    next_of_kin_address = models.TextField(blank=True)

    # ── Timestamps ────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = 'Staff Profile'
        verbose_name_plural = 'Staff Profiles'

    def __str__(self):
        return f"{self.full_name} ({self.staff_id})"

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(p for p in parts if p)

    @property
    def leave_days_remaining(self):
        return self.leave_entitlement_days - self.leave_days_taken

    def save(self, *args, **kwargs):
        if not self.staff_id:
            self.staff_id = self._generate_staff_id()
        super().save(*args, **kwargs)

    def _generate_staff_id(self):
        # Format: SCH_INITIALS/STAFF/YEAR/SEQUENCE e.g. ITA/STF/2026/0001
        initials = ''.join(
            word[0].upper()
            for word in self.school.name.split()[:3]
        )
        year = timezone.now().year
        last = StaffProfile.objects.filter(
            school=self.school
        ).order_by('-created_at').first()
        if last and last.staff_id:
            try:
                seq = int(last.staff_id.split('/')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{initials}/STF/{year}/{seq:04d}"