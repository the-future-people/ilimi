from django.db import models
from django.utils.text import slugify


class School(models.Model):
    STATUS_CHOICES = [
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
    ]

    CURRICULUM_GES = 'ges'
    CURRICULUM_CAMBRIDGE = 'cambridge'
    CURRICULUM_HYBRID = 'hybrid'

    CURRICULUM_CHOICES = [
        (CURRICULUM_GES, 'GES (Ghana Education Service)'),
        (CURRICULUM_CAMBRIDGE, 'Cambridge'),
        (CURRICULUM_HYBRID, 'Hybrid (GES and Cambridge)'),
    ]

    # Only GES is implemented. The class ladder, the band split between
    # class teachers and subject specialists, the three-term calendar and
    # the lesson note format are all GES-shaped. Cambridge and hybrid are
    # selectable so a school can tell us what they follow, but setup says
    # plainly that support is not ready rather than handing them a GES
    # product wearing a Cambridge label.
    CURRICULUM_SUPPORTED = {CURRICULUM_GES}

    SCHOOL_TYPE_CHOICES = [
        ('basic', 'Basic / JHS'),
        ('shs', 'Senior High School'),
        ('international', 'International School'),
        ('group', 'Multi-branch Group'),
    ]

    STUDENT_COUNT_CHOICES = [
        ('under_100', 'Under 100'),
        ('100_300', '100 – 300'),
        ('300_600', '300 – 600'),
        ('600_plus', '600+'),
    ]

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='Ghana')
    logo = models.ImageField(upload_to='schools/logos/', blank=True, null=True)
    website = models.URLField(blank=True)
    curriculum = models.CharField(
    max_length=20, choices=CURRICULUM_CHOICES, blank=True,
    help_text=(
    'Which curriculum this school follows. Chosen during setup '
    'rather than at registration, so registration stays short.'
        ),
    )
    school_type = models.CharField(
    max_length=20, choices=SCHOOL_TYPE_CHOICES, blank=True
    )
    expected_student_count = models.CharField(
        max_length=20, choices=STUDENT_COUNT_CHOICES, blank=True
    )
    subscription_plan = models.ForeignKey(
        'tenants.SubscriptionPlan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='schools'
    )
    subscription_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='trial'
    )
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    onboarding_complete = models.BooleanField(default=False)
    onboarding_step = models.IntegerField(default=1)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while School.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'School'
        verbose_name_plural = 'Schools'
        ordering = ['name']