from django.db import models
from apps.tenants.models import School, Branch
from apps.academics.models import ClassLevel, Term


class FeeType(models.Model):
    """
    Defines the types of fees a school charges.
    e.g. Tuition, PTA, Sports, Feeding, Boarding, Examination
    """
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name='fee_types'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ['school', 'name']
        verbose_name = 'Fee Type'
        verbose_name_plural = 'Fee Types'

    def __str__(self):
        return f"{self.name} — {self.school.name}"


class FeeStructure(models.Model):
    """
    Defines the amount for a specific fee type,
    scoped to a class level, term, and optionally a branch.
    """
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name='fee_structures'
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='fee_structures'
    )
    fee_type = models.ForeignKey(
        FeeType, on_delete=models.CASCADE, related_name='structures'
    )
    class_level = models.ForeignKey(
        ClassLevel, on_delete=models.CASCADE, related_name='fee_structures'
    )
    term = models.ForeignKey(
        Term, on_delete=models.CASCADE, related_name='fee_structures'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_mandatory = models.BooleanField(
        default=True,
        help_text="Is this fee mandatory for all students in this class level?"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['class_level', 'fee_type']
        unique_together = ['school', 'branch', 'fee_type', 'class_level', 'term']
        verbose_name = 'Fee Structure'
        verbose_name_plural = 'Fee Structures'

    def __str__(self):
        branch_label = f" ({self.branch.name})" if self.branch else ""
        return (
            f"{self.fee_type.name} — {self.class_level.display_name}"
            f" — {self.term.get_name_display()}{branch_label}"
        )