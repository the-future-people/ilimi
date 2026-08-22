from django.db import models


class Assignment(models.Model):
    """
    A piece of work a teacher posts to one of her classroom-subject
    combinations. This is the artifact a parent sees in full when she
    opens her child's classroom — the exact moment that already sold a
    real parent on the feature.

    Deliberately does NOT assume digital submission — a class of young
    children may only ever get a checklist ("done" / "not done") via
    AssignmentCompletion, while an older class might attach real files.
    Same Assignment record either way; only how completion is recorded
    differs, decided per assignment by whichever teacher creates it.
    """

    subject_assignment = models.ForeignKey(
        'academics.SubjectAssignment', on_delete=models.CASCADE,
        related_name='classroom_assignments',
        help_text="Ties this to the exact teacher × subject × classroom × "
                   "term combination it belongs to."
    )
    created_by = models.ForeignKey(
        'tenants.SchoolMember', on_delete=models.SET_NULL, null=True,
        related_name='assignments_created'
    )

    title = models.CharField(max_length=200)
    instructions = models.TextField(
        help_text="The full assignment text — what a parent sees in full "
                   "when she opens it."
    )
    attachment = models.FileField(
        upload_to='classroom/assignments/', null=True, blank=True
    )

    due_date = models.DateField(null=True, blank=True)

    # Set once by the creating teacher — decides whether students/parents
    # can actually upload work against this assignment, or whether it's
    # checklist-only (teacher marks who turned in physical work).
    allows_digital_submission = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-due_date', '-created_at']
        verbose_name = "Assignment"
        verbose_name_plural = "Assignments"

    def __str__(self):
        return f"{self.title} — {self.subject_assignment}"