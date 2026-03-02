from django.db import models
from django.utils import timezone
from apps.tenants.models import School
from apps.academics.models import Term
from apps.students.models import Student
from .fee_structure import FeeStructure


class StudentFee(models.Model):
    """
    Represents a fee assigned to a specific student for a specific term.
    Created either automatically from FeeStructure or manually.
    """
    STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
        ('waived', 'Waived'),
        ('overdue', 'Overdue'),
    ]

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name='student_fees'
    )
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='fees'
    )
    fee_structure = models.ForeignKey(
        FeeStructure, on_delete=models.CASCADE, related_name='student_fees'
    )
    term = models.ForeignKey(
        Term, on_delete=models.CASCADE, related_name='student_fees'
    )
    amount_charged = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Actual amount charged — may differ from structure if discounted."
    )
    amount_paid = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )
    discount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Any discount applied to this fee."
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='unpaid'
    )
    due_date = models.DateField(null=True, blank=True)
    waiver_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['student', 'fee_structure', 'term']
        verbose_name = 'Student Fee'
        verbose_name_plural = 'Student Fees'

    def __str__(self):
        return (
            f"{self.student.full_name} — "
            f"{self.fee_structure.fee_type.name} — "
            f"{self.term.get_name_display()}"
        )

    @property
    def balance(self):
        from decimal import Decimal
        amount_charged = Decimal(str(self.amount_charged))
        discount = Decimal(str(self.discount))
        amount_paid = Decimal(str(self.amount_paid))
        return amount_charged - discount - amount_paid

    @property
    def is_fully_paid(self):
        return self.balance <= 0

    def update_status(self):
        """Recalculate and save status based on payments."""
        if self.status == 'waived':
            return
        if self.is_fully_paid:
            self.status = 'paid'
        elif self.amount_paid > 0:
            self.status = 'partial'
        elif self.due_date and self.due_date < timezone.localdate():
            self.status = 'overdue'
        else:
            self.status = 'unpaid'
        self.save(update_fields=['status'])