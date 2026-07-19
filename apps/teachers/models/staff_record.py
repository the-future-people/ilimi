from django.db import models


class StaffRecord(models.Model):
    RECORD_TYPE_CHOICES = [
        ('award', 'Award'),
        ('commendation', 'Commendation'),
        ('warning', 'Warning'),
        ('disciplinary', 'Disciplinary Note'),
    ]

    staff = models.ForeignKey(
        'teachers.StaffProfile', on_delete=models.CASCADE,
        related_name='records'
    )
    record_type = models.CharField(max_length=15, choices=RECORD_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    date = models.DateField()
    recorded_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, related_name='staff_records_recorded'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.get_record_type_display()}: {self.title} ({self.staff.full_name})"