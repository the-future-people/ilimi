from django.db import models


class SchoolRole(models.Model):
    """
    A named job at one school, holding a bundle of domain permissions.

    Per-school rather than global: schools name these differently and one
    school renaming a role must never affect another. Ghanaian schools also
    distribute the same work differently — a school with no accounts office
    gives finance to its administrator — so the bundle varies too.
    """

    school = models.ForeignKey(
        'tenants.School',
        on_delete=models.CASCADE,
        related_name='roles',
    )
    name = models.CharField(
        max_length=60,
        help_text='What this school calls the job, e.g. Assistant Head Teacher.',
    )
    slug = models.SlugField(
        max_length=40,
        help_text='Stable identifier. Does not change when the name does.',
    )
    description = models.CharField(max_length=255, blank=True)

    is_default = models.BooleanField(
        default=False,
        help_text='Seeded with the school. Can be renamed, cannot be deleted.',
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('school', 'slug')]
        ordering = ['school', 'name']

    def __str__(self):
        return f'{self.name} ({self.school_id})'


class RolePermission(models.Model):
    """One domain, one level, for one role."""

    LEVEL_VIEW = 'view'
    LEVEL_REQUEST = 'request'
    LEVEL_FULL = 'full'

    LEVEL_CHOICES = [
        (LEVEL_VIEW, 'View only'),
        (LEVEL_REQUEST, 'Can request, needs approval'),
        (LEVEL_FULL, 'Full access'),
    ]

    # Ranked so a check for 'request' is satisfied by 'full'.
    LEVEL_RANK = {LEVEL_VIEW: 1, LEVEL_REQUEST: 2, LEVEL_FULL: 3}

    role = models.ForeignKey(
        SchoolRole,
        on_delete=models.CASCADE,
        related_name='permissions',
    )
    domain = models.CharField(max_length=30)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)

    class Meta:
        unique_together = [('role', 'domain')]
        ordering = ['role', 'domain']

    def __str__(self):
        return f'{self.role_id}: {self.domain}={self.level}'

    @property
    def rank(self):
        return self.LEVEL_RANK.get(self.level, 0)