"""
Resolves a Message's audience_type + target into an actual, deduplicated
list of recipients to text. Each resolver returns a list of dicts:
{'name': str, 'phone': str}. Deduplicated by phone number, since a
guardian with two children in the same class should only receive one
SMS, not one per child.
"""

from apps.students.models import Student
from apps.tenants.models import SchoolMember


def resolve_single_guardian(message):
    if not message.target_student:
        return []
    link = message.target_student.student_guardians.filter(is_primary=True).first()
    if not link or not link.guardian or not link.guardian.phone:
        return []
    return [{'name': f"{link.guardian.first_name} {link.guardian.last_name}", 'phone': link.guardian.phone}]


def resolve_single_staff(message):
    if not message.target_staff_member:
        return []
    profile = getattr(message.target_staff_member.user, 'staff_profile', None)
    if not profile or not profile.phone:
        return []
    return [{'name': profile.full_name, 'phone': profile.phone}]


def resolve_class_guardians(message):
    if not message.target_classroom:
        return []
    students = Student.objects.filter(
        current_class=message.target_classroom, status='active'
    ).prefetch_related('student_guardians__guardian')

    seen_phones = set()
    recipients = []
    for student in students:
        link = student.student_guardians.filter(is_primary=True).first()
        if not link or not link.guardian or not link.guardian.phone:
            continue
        phone = link.guardian.phone
        if phone in seen_phones:
            continue
        seen_phones.add(phone)
        recipients.append({'name': f"{link.guardian.first_name} {link.guardian.last_name}", 'phone': phone})
    return recipients


def resolve_all_staff(school):
    members = SchoolMember.objects.filter(
        school=school, is_active=True
    ).select_related('user', 'user__staff_profile')

    seen_phones = set()
    recipients = []
    for member in members:
        profile = getattr(member.user, 'staff_profile', None)
        if not profile or not profile.phone:
            continue
        if profile.phone in seen_phones:
            continue
        seen_phones.add(profile.phone)
        recipients.append({'name': profile.full_name, 'phone': profile.phone})
    return recipients


def resolve_all_guardians(school):
    students = Student.objects.filter(
        school=school, status='active'
    ).prefetch_related('student_guardians__guardian')

    seen_phones = set()
    recipients = []
    for student in students:
        link = student.student_guardians.filter(is_primary=True).first()
        if not link or not link.guardian or not link.guardian.phone:
            continue
        phone = link.guardian.phone
        if phone in seen_phones:
            continue
        seen_phones.add(phone)
        recipients.append({'name': f"{link.guardian.first_name} {link.guardian.last_name}", 'phone': phone})
    return recipients


RESOLVERS = {
    'single_guardian': lambda m: resolve_single_guardian(m),
    'single_staff': lambda m: resolve_single_staff(m),
    'class_guardians': lambda m: resolve_class_guardians(m),
    'all_staff': lambda m: resolve_all_staff(m.school),
    'all_guardians': lambda m: resolve_all_guardians(m.school),
}


def resolve_recipients(message):
    """Single entry point — dispatches to the right resolver by audience_type."""
    resolver = RESOLVERS.get(message.audience_type)
    if not resolver:
        return []
    return resolver(message)