from django.db import transaction


def set_class_teacher(school, classroom, teacher, term, periods_per_week=5):
    """
    Lower-band classes have one teacher for everything. Assigns them to every
    active subject in the school for this classroom and term, reassigning
    existing rows in place rather than deleting them, and makes them form master.

    Returns (created_count, reassigned_count).
    """
    from apps.academics.models import Subject, SubjectAssignment, ClassRoom

    subjects = Subject.objects.filter(
    school=school, is_active=True, subject_type='core'
    )
    existing = {
        a.subject_id: a
        for a in SubjectAssignment.objects.filter(classroom=classroom, term=term)
    }

    created = 0
    reassigned = 0

    with transaction.atomic():
        for subject in subjects:
            row = existing.get(subject.id)
            if row is None:
                SubjectAssignment.objects.create(
                    classroom=classroom,
                    subject=subject,
                    teacher=teacher,
                    term=term,
                    periods_per_week=periods_per_week,
                )
                created += 1
            elif row.teacher_id != (teacher.id if teacher else None):
                row.teacher = teacher
                row.save(update_fields=['teacher'])
                reassigned += 1

        # One teacher, one form class — release any other class they hold.
        if teacher is not None:
            ClassRoom.objects.filter(
                school=school,
                academic_year=classroom.academic_year,
                form_teacher=teacher,
                is_active=True,
            ).exclude(pk=classroom.pk).update(form_teacher=None)

        classroom.form_teacher = teacher
        classroom.save(update_fields=['form_teacher'])

    return created, reassigned