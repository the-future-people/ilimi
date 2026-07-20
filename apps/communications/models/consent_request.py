import uuid
from django.db import models
from django.utils import timezone
from .excursion import Excursion


def consent_signature_path(instance, filename):
    return f"consent_signatures/{instance.student.school.id}/{instance.token}.png"

def consent_pdf_path(instance, filename):
    return f"consent_forms/{instance.student.school.id}/{instance.token}.pdf"


class ConsentRequest(models.Model):
    CONSENT_TYPE_CHOICES = [
        ('first_aid', 'First Aid Administration'),
        ('image_use', "Use of Child's Image / Likeness"),
        ('excursion', 'Excursion / Trip'),
        ('other', 'Other'),
    ]

    METHOD_CHOICES = [
        ('digital_link', 'Digital Link'),
        ('manual', 'Manual (Physical Signature on File)'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('granted', 'Granted'),
        ('denied', 'Denied'),
        ('expired', 'Expired'),
    ]

    student = models.ForeignKey(
        'students.Student', on_delete=models.CASCADE, related_name='consent_requests'
    )
    guardian = models.ForeignKey(
        'students.Guardian', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='consent_requests'
    )
    consent_type = models.CharField(max_length=15, choices=CONSENT_TYPE_CHOICES)
    excursion = models.ForeignKey(
        Excursion, on_delete=models.CASCADE,
        null=True, blank=True, related_name='consent_requests'
    )

    method = models.CharField(max_length=15, choices=METHOD_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    signed_name = models.CharField(max_length=200, blank=True)
    signature_image = models.ImageField(
        upload_to=consent_signature_path, null=True, blank=True
    )
    pdf_file = models.FileField(
        upload_to=consent_pdf_path, null=True, blank=True
    )
    response_notes = models.TextField(blank=True)

    requested_by = models.ForeignKey(
        'tenants.SchoolMember', on_delete=models.SET_NULL,
        null=True, related_name='sent_consent_requests'
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_consent_type_display()} — {self.student.full_name} ({self.status})"

    @property
    def is_expired(self):
        if self.method != 'digital_link' or not self.expires_at:
            return False
        return timezone.now() > self.expires_at and self.status == 'pending'