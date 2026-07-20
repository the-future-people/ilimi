from datetime import timedelta

from django.utils import timezone

from apps.students.models import Student
from apps.communications.models import Excursion, ConsentRequest


def send_consent_sms(consent_request, link):
    try:
        from apps.notifications.services.sms import send_sms
        student_name = consent_request.student.full_name
        type_label = consent_request.get_consent_type_display()
        send_sms(
            consent_request.guardian.phone if consent_request.guardian else '',
            f"{consent_request.student.school.name}: Please review and respond to a consent "
            f"request for {student_name} ({type_label}): {link}",
        )
    except Exception:
        pass  # SMS failure shouldn't block the request from being created


def build_consent_link(base_url, token):
    return f"{base_url}/consent/{token}"


def request_excursion_consents(excursion, member, base_url):
    """
    Creates a digital consent request for every active student in the
    excursion's linked classrooms who doesn't already have one, and
    texts each one's primary guardian a link. Returns (created_count,
    already_existing_count).
    """
    classroom_ids = excursion.classrooms.values_list('id', flat=True)
    students = Student.objects.filter(
        school=excursion.school, current_class_id__in=classroom_ids, status='active'
    ).prefetch_related('student_guardians__guardian')

    existing_student_ids = set(
        ConsentRequest.objects.filter(excursion=excursion).values_list('student_id', flat=True)
    )

    created_count = 0
    for student in students:
        if student.id in existing_student_ids:
            continue

        primary_link = next(iter(student.student_guardians.all()), None)
        guardian = primary_link.guardian if primary_link else None

        cr = ConsentRequest.objects.create(
            student=student,
            guardian=guardian,
            consent_type='excursion',
            excursion=excursion,
            method='digital_link',
            status='pending',
            requested_by=member,
            expires_at=timezone.now() + timedelta(days=7),
        )
        if guardian and guardian.phone:
            send_consent_sms(cr, build_consent_link(base_url, cr.token))
        created_count += 1

    return created_count, len(existing_student_ids)


def create_consent_request(member, validated_data, base_url):
    """
    Creates a single ConsentRequest — either an immediately-resolved
    manual record, or a pending digital one that texts the guardian a
    link. Returns the created ConsentRequest.
    """
    is_manual = validated_data['method'] == 'manual'

    cr = ConsentRequest.objects.create(
        student=validated_data['student'],
        guardian=validated_data.get('guardian'),
        consent_type=validated_data['consent_type'],
        excursion=validated_data.get('excursion'),
        method=validated_data['method'],
        status=validated_data.get('status', 'pending') if is_manual else 'pending',
        signed_name=validated_data.get('signed_name', ''),
        response_notes=validated_data.get('response_notes', ''),
        requested_by=member,
        responded_at=timezone.now() if is_manual else None,
        expires_at=None if is_manual else timezone.now() + timedelta(days=7),
    )

    if not is_manual and cr.guardian and cr.guardian.phone:
        send_consent_sms(cr, build_consent_link(base_url, cr.token))

    return cr


def respond_to_consent_request(token, decision, signed_name='', signature_file=None):
    """
    Records a parent's response to a pending digital consent request.
    Raises ConsentRequest.DoesNotExist if the token is invalid, and
    ValueError if the request is no longer pending or has expired
    (callers should translate these into the appropriate HTTP response).
    """
    cr = ConsentRequest.objects.get(token=token)

    if cr.status != 'pending':
        raise ValueError('already_responded')
    if cr.is_expired:
        cr.status = 'expired'
        cr.save(update_fields=['status'])
        raise ValueError('expired')

    if decision not in ('granted', 'denied'):
        raise ValueError('invalid_decision')

    cr.status = decision
    cr.signed_name = signed_name
    cr.responded_at = timezone.now()
    if signature_file:
        cr.signature_image = signature_file
    cr.save(update_fields=['status', 'signed_name', 'responded_at', 'signature_image'])

    return cr

import base64
from django.core.mail import EmailMessage
from django.conf import settings

from apps.documents.services.pdf import render_pdf


def _build_consent_html(consent_request):
    student = consent_request.student
    school = student.school
    excursion = consent_request.excursion

    signature_html = ''
    if consent_request.signature_image:
        try:
            with consent_request.signature_image.open('rb') as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
            signature_html = f'<img src="data:image/png;base64,{encoded}" style="height:60px;" />'
        except Exception:
            signature_html = ''

    excursion_block = ''
    if excursion:
        excursion_block = f"""
            <p><strong>Excursion:</strong> {excursion.name}</p>
            <p><strong>Date:</strong> {excursion.date}</p>
            <p><strong>Location:</strong> {excursion.location or '—'}</p>
            <p>{excursion.description}</p>
        """

    status_label = {
        'granted': 'CONSENT GRANTED',
        'denied': 'CONSENT DENIED',
        'pending': 'PENDING RESPONSE',
        'expired': 'EXPIRED — NO RESPONSE RECEIVED',
    }.get(consent_request.status, consent_request.status.upper())

    return f"""
    <html>
    <head>
        <style>
            body {{ font-family: sans-serif; padding: 40px; color: #1a2946; }}
            h1 {{ font-size: 18px; border-bottom: 2px solid #e8a021; padding-bottom: 8px; }}
            .status {{ font-weight: bold; font-size: 14px; margin: 16px 0; }}
            .field {{ margin-bottom: 6px; }}
            .signature-block {{ margin-top: 40px; border-top: 1px solid #ccc; padding-top: 12px; }}
        </style>
    </head>
    <body>
        <h1>{school.name} — Consent Form</h1>
        <div class="field"><strong>Student:</strong> {student.full_name} ({student.student_id})</div>
        <div class="field"><strong>Consent Type:</strong> {consent_request.get_consent_type_display()}</div>
        {excursion_block}
        <div class="status">{status_label}</div>
        <div class="signature-block">
            <p><strong>Signed by:</strong> {consent_request.signed_name or '—'}</p>
            <p><strong>Date:</strong> {consent_request.responded_at.strftime('%d %B %Y, %H:%M') if consent_request.responded_at else '—'}</p>
            {signature_html}
        </div>
    </body>
    </html>
    """


def generate_consent_pdf(consent_request, base_url=None):
    """Renders and saves the consent form PDF, if not already generated."""
    if consent_request.pdf_file:
        return consent_request

    html = _build_consent_html(consent_request)
    pdf_bytes = render_pdf(html, base_url=base_url)

    from django.core.files.base import ContentFile
    consent_request.pdf_file.save(f"{consent_request.token}.pdf", ContentFile(pdf_bytes), save=True)
    return consent_request


def send_consent_pdf_email(consent_request, base_url=None):
    """
    Generates the PDF if needed and emails it as a real attachment.
    Returns True if sent, False if no guardian email was available.
    """
    generate_consent_pdf(consent_request, base_url=base_url)

    email = consent_request.guardian.email if consent_request.guardian else ''
    if not email:
        return False

    student_name = consent_request.student.full_name
    school_name = consent_request.student.school.name

    message = EmailMessage(
        subject=f"{school_name} — Consent Form for {student_name}",
        body=f"Please find attached the consent form for {student_name} ({consent_request.get_consent_type_display()}).",
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'webmaster@localhost'),
        to=[email],
    )
    with consent_request.pdf_file.open('rb') as f:
        message.attach(f"consent_{consent_request.token}.pdf", f.read(), 'application/pdf')
    message.send(fail_silently=True)
    return True


def build_whatsapp_share_link(consent_request, base_url):
    """
    Generates the PDF if needed and returns a wa.me link with a
    pre-filled message containing the PDF's URL. WhatsApp (outside the
    paid Business API) can't auto-attach a file into a chat, so the
    parent gets a message with a link to open/download instead.
    """
    generate_consent_pdf(consent_request, base_url=base_url)

    phone = ''
    if consent_request.guardian:
        phone = consent_request.guardian.whatsapp_number or consent_request.guardian.phone
    digits = ''.join(c for c in phone if c.isdigit())

    # Normalize to international format for WhatsApp's click-to-chat links.
    # Ghanaian numbers are typically stored in local format (e.g. 0540687949);
    # wa.me requires the country code with no leading 0 (e.g. 233540687949).
    if digits.startswith('0') and len(digits) == 10:
        digits = '233' + digits[1:]

    pdf_url = f"{base_url}{consent_request.pdf_file.url}"
    student_name = consent_request.student.full_name
    school_name = consent_request.student.school.name
    message = (
        f"{school_name}: Here is the consent form for {student_name} "
        f"({consent_request.get_consent_type_display()}): {pdf_url}"
    )

    import urllib.parse
    encoded_message = urllib.parse.quote(message)
    wa_link = f"https://wa.me/{digits}?text={encoded_message}" if digits else None

    return {'pdf_url': pdf_url, 'whatsapp_link': wa_link}

def create_excursion(member, validated_data):
    """Creates an Excursion, handling the M2M classrooms field correctly
    (can't be passed through Model.objects.create())."""
    data = dict(validated_data)
    classrooms = data.pop('classrooms', [])

    excursion = Excursion.objects.create(
        school=member.school, created_by=member, **data
    )
    if classrooms:
        excursion.classrooms.set(classrooms)

    return excursion