from django.db import models
from apps.academics.models import ClassRoom, AcademicYear


class StudentClassHistory(models.Model):
    """
    Tracks which class a student was in for each academic year.
    Allows viewing a student's full academic progression.
    """
    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE,
        related_name='class_history'
    )
    classroom = models.ForeignKey(
        ClassRoom, on_delete=models.CASCADE,
        related_name='student_history'
    )
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.CASCADE,
        related_name='student_history'
    )
    is_current = models.BooleanField(default=True)
    promoted = models.BooleanField(
        null=True, blank=True,
        help_text="Was the student promoted at end of year? Null = not yet determined"
    )
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'academic_year')
        ordering = ['-academic_year__start_date']

    def __str__(self):
        return f"{self.student.full_name} — {self.classroom} ({self.academic_year.name})"

    def save(self, *args, **kwargs):
        # Only one current class history per student
        if self.is_current:
            StudentClassHistory.objects.filter(
                student=self.student, is_current=True
            ).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)