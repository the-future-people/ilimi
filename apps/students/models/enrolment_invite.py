import uuid
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone


def invite_photo_path(instance, filename):
    ext = filename.split('.')[-1]
    return f"enrolment_invites/{instance.school.id}/{instance.token}.{ext}"


class EnrolmentInvite(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    school = models.ForeignKey(
        'tenants.School', on_delete=models.CASCADE, related_name='enrolment_invites'
    )
    invited_by = models.ForeignKey(
        'tenants.SchoolMember', on_delete=models.SET_NULL,
        null=True, related_name='sent_enrolment_invites'
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    prospective_first_name = models.CharField(max_length=100)
    prospective_last_name = models.CharField(max_length=100)
    parent_phone = models.CharField(max_length=20)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    submitted_data = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    submitted_photo = models.ImageField(
        upload_to=invite_photo_path, null=True, blank=True
    )
    submitted_at = models.DateTimeField(null=True, blank=True)

    reviewed_by = models.ForeignKey(
        'tenants.SchoolMember', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_enrolment_invites'
    )
    review_remarks = models.TextField(blank=True)

    created_student = models.ForeignKey(
        'students.Student', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='enrolment_invite'
    )

    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.prospective_first_name} {self.prospective_last_name} ({self.status})"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at and self.status == 'pending'

    @property
    def prospective_full_name(self):
        return f"{self.prospective_first_name} {self.prospective_last_name}"