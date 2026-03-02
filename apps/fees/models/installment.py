from django.db import models
from django.utils import timezone
from .student_fee import StudentFee


class InstallmentPlan(models.Model):
    """
    Defines an installment plan for a student fee.
    Breaks a fee into multiple scheduled payments.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    student_fee = models.OneToOneField(
        StudentFee, on_delete=models.CASCADE, related_name='installment_plan'
    )
    number_of_installments = models.PositiveIntegerField()
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default='active'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Installment Plan'
        verbose_name_plural = 'Installment Plans'

    def __str__(self):
        return (
            f"Installment Plan — {self.student_fee.student.full_name} — "
            f"{self.student_fee.fee_structure.fee_type.name}"
        )

    @property
    def total_amount(self):
        return self.student_fee.amount_charged - self.student_fee.discount

    @property
    def amount_per_installment(self):
        if self.number_of_installments:
            return round(self.total_amount / self.number_of_installments, 2)
        return 0


class Installment(models.Model):
    """
    A single installment within an installment plan.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    ]

    plan = models.ForeignKey(
        InstallmentPlan, on_delete=models.CASCADE, related_name='installments'
    )
    installment_number = models.PositiveIntegerField()
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='pending'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['installment_number']
        unique_together = ['plan', 'installment_number']
        verbose_name = 'Installment'
        verbose_name_plural = 'Installments'

    def __str__(self):
        return (
            f"Installment {self.installment_number} — "
            f"{self.plan.student_fee.student.full_name} — "
            f"GHS {self.amount_due}"
        )

    @property
    def balance(self):
        return self.amount_due - self.amount_paid

    def update_status(self):
        if self.amount_paid >= self.amount_due:
            self.status = 'paid'
        elif self.due_date < timezone.localdate():
            self.status = 'overdue'
        else:
            self.status = 'pending'
        self.save(update_fields=['status'])