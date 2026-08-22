from django.db import models


class ClassworkRecord(models.Model):
    """
    One student's record against one piece of classwork.

    Carries both the completion state (did they do it, did they hand it in)
    and the score, so a teacher marking homework performs one action rather
    than entering the same work twice in two systems.

    score is only meaningful when the parent Classwork has a component_type.
    """

    STATUS_CHOICES = [
        ('not_done', 'Not Done'),
        ('done', 'Done'),
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
        ('excused', 'Excused'),
    ]

    school      = models.ForeignKey('tenants.School', on_delete=models.CASCADE, related_name='classwork_records')
    student     = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='classwork_records')
    classwork   = models.ForeignKey('academics.Classwork', on_delete=models.CASCADE, related_name='records')

    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_done')

    score       = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    remarks     = models.TextField(blank=True)

    submitted_file = models.FileField(upload_to='classwork_submissions/', null=True, blank=True)
    submitted_at   = models.DateTimeField(null=True, blank=True)
    submitted_by   = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='classwork_submissions',
        help_text='Who uploaded — the parent today, the student once they have logins.',
    )

    marked_by   = models.ForeignKey(
        'tenants.SchoolMember',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='marked_classwork_records',
    )
    marked_at   = models.DateTimeField(null=True, blank=True)

    locked      = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'classwork')
        ordering = ['student__last_name', 'student__first_name']

    def __str__(self):
        return f"{self.student} - {self.classwork} - {self.status}"