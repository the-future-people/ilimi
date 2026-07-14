import random
from django.db import models
from django.utils import timezone
from datetime import timedelta


def generate_otp():
    return str(random.randint(100000, 999999))


def otp_expiry():
    return timezone.now() + timedelta(minutes=10)


def pending_expiry():
    return timezone.now() + timedelta(hours=2)


class PendingRegistration(models.Model):
    """
    Holds all data collected during registration (school info, personal
    details, hashed password) plus the OTP, until phone verification
    succeeds. No real User, School, or SchoolMember exists until then —
    this ensures no unverified/incomplete accounts ever touch the main
    tables. Rows here expire and can be safely purged if abandoned.
    """
    MAX_ATTEMPTS = 3

    # ── Personal details ──────────────────────────────────────────────
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    password_hash = models.CharField(max_length=255)
    position_title = models.CharField(max_length=20, blank=True)

    # ── School details ───────────────────────────────────────────────
    school_name = models.CharField(max_length=255)
    school_email = models.EmailField(blank=True)
    school_phone = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='Ghana')
    school_type = models.CharField(max_length=20, blank=True)
    expected_student_count = models.CharField(max_length=20, blank=True)

    # ── OTP ───────────────────────────────────────────────────────────
    otp = models.CharField(max_length=6, default=generate_otp)
    otp_created_at = models.DateTimeField(auto_now_add=True)
    otp_expires_at = models.DateTimeField(default=otp_expiry)
    attempts = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=pending_expiry)

    class Meta:
        verbose_name = 'Pending Registration'
        verbose_name_plural = 'Pending Registrations'

    def __str__(self):
        return f"Pending: {self.email} — {self.school_name}"

    @property
    def is_otp_expired(self):
        return timezone.now() > self.otp_expires_at

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def regenerate_otp(self):
        self.otp = generate_otp()
        self.otp_created_at = timezone.now()
        self.otp_expires_at = otp_expiry()
        self.attempts = 0
        self.save(update_fields=['otp', 'otp_created_at', 'otp_expires_at', 'attempts'])
        return self.otp

    def verify(self, code):
        """
        Attempt to verify the OTP code.
        Returns (success: bool, message: str)
        """
        if self.is_expired:
            return False, 'This registration session has expired. Please start again.'
        if self.is_otp_expired:
            return False, 'This code has expired. Please request a new one.'
        if self.attempts >= self.MAX_ATTEMPTS:
            return False, 'Maximum attempts exceeded. Please request a new code.'

        self.attempts += 1

        if self.otp != code:
            self.save(update_fields=['attempts'])
            remaining = self.MAX_ATTEMPTS - self.attempts
            return False, f'Invalid code. {remaining} attempt(s) remaining.'

        return True, 'Phone number verified successfully.'