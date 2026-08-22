from django.db import models


class ClassworkSubmission(models.Model):
    """
    One uploaded file against a student's classwork record.

    Separate from ClassworkRecord.submitted_file because a child
    photographing an exercise book needs several pages, not one.
    """

    record      = models.ForeignKey(
        'academics.ClassworkRecord',
        on_delete=models.CASCADE,
        related_name='submissions',
    )
    file        = models.FileField(upload_to='classwork_submissions/')
    caption     = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='uploaded_classwork_files',
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.record.student} - {self.file.name}"