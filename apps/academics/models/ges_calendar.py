from django.db import models


class GESCalendarTemplate(models.Model):
    """
    The GES-published academic calendar for a given year.

    Global reference data, seeded manually each May when GES releases the
    calendar (there is no official feed or API — it goes out as a press
    release). Schools pre-fill their own AcademicYear from this, then edit
    freely; nothing here is binding on a school.
    """

    name = models.CharField(
        max_length=20, unique=True,
        help_text="e.g. '2026/2027'"
    )
    start_date = models.DateField(help_text="First day of Term 1")
    end_date = models.DateField(help_text="Official end of the academic year")

    exam_start_date = models.DateField(
        null=True, blank=True, help_text="BECE start date, if published"
    )
    exam_end_date = models.DateField(
        null=True, blank=True, help_text="BECE end date, if published"
    )

    source_note = models.CharField(
        max_length=255, blank=True,
        help_text="Where this was sourced from, for verification later"
    )
    published_on = models.DateField(
        null=True, blank=True,
        help_text="Date GES issued the release"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Uncheck to hide from the setup dropdown without deleting"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name = "GES Calendar Template"
        verbose_name_plural = "GES Calendar Templates"

    def __str__(self):
        return f"GES {self.name}"


class GESCalendarTermTemplate(models.Model):
    """
    One term within a GESCalendarTemplate.

    Mirrors Term's TERM_CHOICES exactly so the setup service can map
    straight across without translation.
    """

    TERM_CHOICES = [
        ('term_1', 'Term 1'),
        ('term_2', 'Term 2'),
        ('term_3', 'Term 3'),
    ]

    calendar = models.ForeignKey(
        GESCalendarTemplate, on_delete=models.CASCADE, related_name='terms'
    )
    name = models.CharField(max_length=10, choices=TERM_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()

    vacation_start_date = models.DateField(null=True, blank=True)
    vacation_end_date = models.DateField(null=True, blank=True)

    # GES publishes Term 1's mid-term dates but leaves Terms 2 and 3
    # to individual schools, so these are frequently blank.
    midterm_start_date = models.DateField(null=True, blank=True)
    midterm_end_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('calendar', 'name')
        ordering = ['name']
        verbose_name = "GES Calendar Term Template"
        verbose_name_plural = "GES Calendar Term Templates"

    def __str__(self):
        return f"GES {self.calendar.name} — {self.get_name_display()}"