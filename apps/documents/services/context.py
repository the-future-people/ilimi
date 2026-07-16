from django.utils import timezone


def build_standard_context(student):
    """
    Assembles the standard token context available to every document
    template, regardless of document type. Template-specific extra
    fields (e.g. embassy_name) are merged in separately by the caller.
    """
    school = student.school
    current_class = student.current_class

    primary_link = (
        student.student_guardians.filter(is_primary=True).first()
        or student.student_guardians.first()
    )
    guardian = primary_link.guardian if primary_link else None

    return {
        "student_name": student.full_name,
        "student_id": student.student_id,
        "class_name": str(current_class) if current_class else "",
        "date": timezone.now().strftime("%B %d, %Y"),
        "guardian_name": f"{guardian.first_name} {guardian.last_name}".strip() if guardian else "",
        "guardian_phone": guardian.phone if guardian else "",
        "school_name": school.name,
        "school_address": school.address,
        "school_phone": school.phone,
        "school_logo_url": school.logo.url if school.logo else "",
    }