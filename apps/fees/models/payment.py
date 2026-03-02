from django.db import models
from apps.tenants.models import School
from apps.accounts.models import User
from .student_fee import StudentFee


class Payment(models.Model):
    """
    Records an actual payment made against a student fee.
    Supports cash, MoMo, bank transfer, and Paystack (online).
    """
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('momo', 'Mobile Money (MoMo)'),
        ('bank_transfer', 'Bank Transfer'),
        ('paystack', 'Paystack (Online)'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    ]

    MOMO_PROVIDER_CHOICES = [
        ('mtn', 'MTN MoMo'),
        ('vodafone', 'Vodafone Cash'),
        ('airteltigo', 'AirtelTigo Money'),
    ]

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name='payments'
    )
    student_fee = models.ForeignKey(
        StudentFee, on_delete=models.CASCADE, related_name='payments'
    )
    receipt_number = models.CharField(max_length=30, unique=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES
    )
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default='successful'
    )

    # ── Cash ──────────────────────────────────────────────────────────
    received_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='payments_received',
        help_text="Staff member who received the cash payment."
    )

    # ── MoMo ──────────────────────────────────────────────────────────
    momo_provider = models.CharField(
        max_length=15, choices=MOMO_PROVIDER_CHOICES, blank=True
    )
    momo_number = models.CharField(max_length=20, blank=True)
    momo_transaction_id = models.CharField(max_length=100, blank=True)

    # ── Bank Transfer ─────────────────────────────────────────────────
    bank_name = models.CharField(max_length=100, blank=True)
    bank_reference = models.CharField(max_length=100, blank=True)

    # ── Paystack ──────────────────────────────────────────────────────
    paystack_reference = models.CharField(max_length=100, blank=True)
    paystack_transaction_id = models.CharField(max_length=100, blank=True)

    # ── Meta ──────────────────────────────────────────────────────────
    payment_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-payment_date', '-created_at']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

    def __str__(self):
        return (
            f"Receipt {self.receipt_number} — "
            f"{self.student_fee.student.full_name} — "
            f"GHS {self.amount}"
        )

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = self._generate_receipt_number()
        super().save(*args, **kwargs)
        # Update student fee status and amount paid after every payment
        if self.status == 'successful':
            self._update_student_fee()

    def _generate_receipt_number(self):
        from apps.tenants.models import School
        initials = ''.join(
            word[0].upper()
            for word in self.school.name.split()[:3]
        )
        from django.utils import timezone
        year = timezone.now().year
        last = Payment.objects.filter(
            school=self.school
        ).order_by('-created_at').first()
        if last and last.receipt_number:
            try:
                seq = int(last.receipt_number.split('/')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{initials}/RCP/{year}/{seq:05d}"

    def _update_student_fee(self):
        student_fee = self.student_fee
        total_paid = student_fee.payments.filter(
            status='successful'
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        student_fee.amount_paid = total_paid
        student_fee.save(update_fields=['amount_paid'])
        student_fee.update_status()