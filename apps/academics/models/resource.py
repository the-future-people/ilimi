from django.db import models


class Resource(models.Model):
    """
    Teaching material attached to a class and subject but not to a
    specific piece of work — a reading, a worksheet, a photo of the board.
    """

    school     = models.ForeignKey('tenants.School', on_delete=models.CASCADE, related_name='resources')
    branch     = models.ForeignKey('tenants.Branch', on_delete=models.SET_NULL, null=True, blank=True)
    classroom  = models.ForeignKey('academics.ClassRoom', on_delete=models.CASCADE, related_name='resources')
    subject    = models.ForeignKey('academics.Subject', on_delete=models.CASCADE, related_name='resources')
    term       = models.ForeignKey('academics.Term', on_delete=models.CASCADE, related_name='resources')

    title      = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file       = models.FileField(upload_to='resources/', null=True, blank=True)
    link       = models.URLField(blank=True, help_text='External link, if there is no file.')

    visible_to_parents = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        'tenants.SchoolMember',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_resources',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.subject} - {self.classroom}"