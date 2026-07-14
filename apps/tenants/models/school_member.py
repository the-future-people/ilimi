from django.db import models


class SchoolMember(models.Model):
    ROLE_CHOICES = [
        ('school_admin', 'School Administrator'),
        ('branch_manager', 'Branch Manager'),
        ('teacher', 'Teacher'),
        ('accountant', 'Accountant'),
        ('receptionist', 'Receptionist'),
    ]

    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='school_memberships'
    )
    school = models.ForeignKey(
        'tenants.School',
        on_delete=models.CASCADE,
        related_name='members'
    )
    branch = models.ForeignKey(
        'tenants.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members'
    )
    POSITION_CHOICES = [
        ('proprietor', 'Proprietor / Owner'),
        ('head_teacher', 'Head Teacher / Principal'),
        ('administrator', 'Administrator'),
        ('other', 'Other'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    position_title = models.CharField(
        max_length=20, choices=POSITION_CHOICES, blank=True,
        help_text="Descriptive title for this person's position at the school — informational only, does not affect permissions."
    )
    is_active = models.BooleanField(default=True)
    has_seen_tour = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.full_name} - {self.get_role_display()} at {self.school.name}'

    @property
    def is_school_level(self):
        return self.branch is None

    @property
    def is_branch_level(self):
        return self.branch is not None

    class Meta:
        verbose_name = 'School Member'
        verbose_name_plural = 'School Members'
        unique_together = ['user', 'school', 'role']