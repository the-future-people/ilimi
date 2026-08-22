from django.db import models


class AssignmentCompletion(models.Model):
    """
    How one student's status against one assignment is recorded. Two
    genuinely different tracks share this one model:

    - Checklist track (allows_digital_submission=False on the parent
      Assignment): a teacher just marks done/not done for physical work
      she's already looking at.
    - Digital track: a real file gets attached, status becomes a real
      submission workflow (submitted -> graded).

    No student-login concept exists yet, so any digital upload today is
    performed by a parent on the child's behalf, not the student directly.
    """

    STATUS_CHOICES = [
        ('not_done', 'Not Done'),
        ('done', 'Done'),
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
    ]

    assignment = models.ForeignKey(
        'classroom.Assignment', on_delete=models.CASCADE,
        related_name='completions'
    )
    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE,
        related_name='assignment_completions'
    )

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='not_done')
    submitted_file = models.FileField(
        upload_to='classroom/submissions/', null=True, blank=True
    )
    submitted_at = models.DateTimeField(null=True, blank=True)

    marked_by = models.ForeignKey(
        'tenants.SchoolMember', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assignment_completions_marked',
        help_text="Which teacher marked this — relevant for the checklist "
                   "track where a teacher sets status directly."
    )
    marked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('assignment', 'student')
        ordering = ['student__last_name', 'student__first_name']
        verbose_name = "Assignment Completion"
        verbose_name_plural = "Assignment Completions"

    def __str__(self):
        return f"{self.student.full_name} — {self.assignment.title} ({self.get_status_display()})"