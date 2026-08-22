from django.db import models


class Classwork(models.Model):
    """
    Any piece of work a teacher sets or administers: homework, class exercise,
    quiz, class test, group work. Scoped to classroom + subject + term rather
    than SubjectAssignment, so records survive mid-term teacher changes.

    If component_type is set, the work counts toward the CA class score.
    If it is null, the work is tracked and visible but never graded.
    """

    WORK_TYPE_CHOICES = [
        ('homework', 'Homework'),
        ('exercise', 'Class Exercise'),
        ('quiz', 'Quiz'),
        ('test', 'Class Test'),
        ('group_work', 'Group Work'),
        ('project', 'Project'),
    ]

    school          = models.ForeignKey('tenants.School', on_delete=models.CASCADE, related_name='classwork')
    branch          = models.ForeignKey('tenants.Branch', on_delete=models.SET_NULL, null=True, blank=True)
    classroom       = models.ForeignKey('academics.ClassRoom', on_delete=models.CASCADE, related_name='classwork')
    subject         = models.ForeignKey('academics.Subject', on_delete=models.CASCADE, related_name='classwork')
    term            = models.ForeignKey('academics.Term', on_delete=models.CASCADE, related_name='classwork')

    work_type       = models.CharField(max_length=20, choices=WORK_TYPE_CHOICES, default='homework')

    component_type  = models.ForeignKey(
        'academics.CAComponentType',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='components',
        help_text='Set to count this work toward the CA class score. Null means ungraded.',
    )

    name            = models.CharField(max_length=100)
    instructions    = models.TextField(blank=True)
    attachment      = models.FileField(upload_to='classwork/', null=True, blank=True)

    max_score       = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=100)
    date            = models.DateField(help_text='Date the work was set or administered.')
    due_date        = models.DateField(null=True, blank=True)

    visible_to_parents        = models.BooleanField(default=True)
    allows_digital_submission = models.BooleanField(default=False)

    created_by      = models.ForeignKey(
        'tenants.SchoolMember',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_classwork',
    )
    created_at      = models.DateTimeField(auto_now_add=True, null=True)
    updated_at      = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ['-date', 'name']
        unique_together = ('classroom', 'subject', 'term', 'name')

    def __str__(self):
        return f"{self.name} - {self.subject} - {self.classroom}"

    @property
    def is_graded(self):
        return self.component_type_id is not None