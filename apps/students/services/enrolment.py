from apps.core.models import Occupation
from apps.academics.models import AcademicYear
from apps.students.models import (
    Student, Guardian, StudentGuardian, EmergencyContact, StudentClassHistory,
)


def create_student_with_guardians(school, branch, validated_data):
    """
    Shared creation logic for enrolling a student with nested guardians,
    emergency contacts, and sibling linkage.

    Used by both the direct admin Enrolment Wizard and the Parent
    Self-Service Enrolment Link approval flow, so both paths behave
    identically and stay in sync automatically.

    `validated_data` should already be validated (e.g. against
    StudentEnrolSerializer). This function pops nested keys off a
    shallow copy, so the caller's original dict is left untouched.
    """
    data = dict(validated_data)
    guardians_data = data.pop('guardians', [])
    emergency_contacts_data = data.pop('emergency_contacts', [])
    sibling_students = data.pop('sibling_ids', [])

    student = Student.objects.create(
        school=school,
        branch=branch,
        **data,
    )

    if sibling_students:
        student.siblings.add(*sibling_students)

    for g_data in guardians_data:
        g_data = dict(g_data)
        is_primary = g_data.pop('is_primary', False)
        occupation_name = g_data.pop('occupation_name', '').strip()
        occupation = None
        if occupation_name:
            occupation, _ = Occupation.objects.get_or_create(name=occupation_name)
        guardian = Guardian.objects.create(occupation=occupation, **g_data)
        StudentGuardian.objects.create(
            student=student,
            guardian=guardian,
            is_primary=is_primary,
        )

    for ec_data in emergency_contacts_data:
        EmergencyContact.objects.create(student=student, **ec_data)

    try:
        current_year = AcademicYear.objects.get(school=school, is_current=True)
        if student.current_class:
            StudentClassHistory.objects.create(
                student=student,
                classroom=student.current_class,
                academic_year=current_year,
                is_current=True,
            )
    except AcademicYear.DoesNotExist:
        pass

    from apps.students.services.notification_service import notify_guardian_enrolment
    notify_guardian_enrolment(student, school)

    return student