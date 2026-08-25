from django.db import models


class LessonPlan(models.Model):
    """
    One week's learning plan for one subject in one class, in the GES format.

    A teacher writes one of these per class per subject per week — so a
    facilitator taking RME across four classes writes four every week.
    Submitted weekly and vetted by the head of academics.

    Terminology follows the current curriculum: strand, sub-strand,
    indicator, content standard, TLR, learners, facilitator.
    """

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('vetted', 'Vetted'),
        ('returned', 'Returned for revision'),
    ]

    school      = models.ForeignKey('tenants.School', on_delete=models.CASCADE, related_name='lesson_plans')
    branch      = models.ForeignKey('tenants.Branch', on_delete=models.SET_NULL, null=True, blank=True)
    classroom   = models.ForeignKey('academics.ClassRoom', on_delete=models.CASCADE, related_name='lesson_plans')
    subject     = models.ForeignKey('academics.Subject', on_delete=models.CASCADE, related_name='lesson_plans')
    term        = models.ForeignKey('academics.Term', on_delete=models.CASCADE, related_name='lesson_plans')

    week_ending = models.DateField(help_text='Friday of the week this plan covers.')
    class_size  = models.PositiveIntegerField(null=True, blank=True)

    strand      = models.CharField(max_length=200, blank=True)
    sub_strand  = models.CharField(max_length=200, blank=True)

    indicator_code        = models.CharField(max_length=50, blank=True, help_text='e.g. B4-4-4-1-1')
    content_standard_code = models.CharField(max_length=50, blank=True, help_text='e.g. B4-4-4-1')
    performance_indicator = models.TextField(blank=True)

    core_competencies = models.TextField(blank=True)
    key_words         = models.TextField(blank=True)
    tlr               = models.TextField(blank=True, help_text='Teaching and learning resources.')
    reference         = models.CharField(max_length=200, blank=True)

    facilitator = models.ForeignKey(
        'tenants.SchoolMember', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='lesson_plans',
    )

    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    submitted_at = models.DateTimeField(null=True, blank=True)

    vetted_by       = models.ForeignKey(
        'tenants.SchoolMember', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='vetted_lesson_plans',
    )
    vetted_at       = models.DateTimeField(null=True, blank=True)
    vetting_remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-week_ending']
        unique_together = ('classroom', 'subject', 'term', 'week_ending')

    def __str__(self):
        return f"{self.subject} - {self.classroom} - week ending {self.week_ending}"

    @property
    def is_editable(self):
        return self.status in ('draft', 'returned')


class LessonPlanDay(models.Model):
    """
    One teaching day within a week's plan, carrying the three phases.
    Days with nothing written are simply not taught that day.
    """

    DAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
    ]

    DAY_ORDER = {d[0]: i for i, d in enumerate(DAY_CHOICES)}

    plan   = models.ForeignKey(
        'academics.LessonPlan', on_delete=models.CASCADE, related_name='days'
    )
    day    = models.CharField(max_length=10, choices=DAY_CHOICES)
    date   = models.DateField(null=True, blank=True)
    period = models.CharField(max_length=50, blank=True, help_text='e.g. 1 hour, Period 3.')

    phase_1_starter = models.TextField(blank=True, help_text='Preparing the brain for learning.')
    phase_2_main    = models.TextField(blank=True, help_text='New learning including assessment.')
    phase_3_plenary = models.TextField(blank=True, help_text='Plenary and reflections.')

    order  = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        unique_together = ('plan', 'day')

    def save(self, *args, **kwargs):
        if not self.order:
            self.order = self.DAY_ORDER.get(self.day, 99)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_day_display()} - {self.plan.sub_strand or self.plan.strand}"

    @property
    def has_content(self):
        return bool(self.phase_1_starter or self.phase_2_main or self.phase_3_plenary)