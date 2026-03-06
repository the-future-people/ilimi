from django.utils import timezone
from django.db import transaction
from decimal import Decimal


def get_default_component_types(school):
    """Returns the school's CA component types ordered by weight descending."""
    from apps.academics.models import CAComponentType
    return CAComponentType.objects.filter(school=school, is_active=True).order_by('-weight', 'order')


def create_default_component_types(school):
    """Creates default CA component types for a newly onboarded school."""
    from apps.academics.models import CAComponentType

    defaults = [
        {'name': 'Class Test',          'weight': Decimal('50.00'), 'order': 1},
        {'name': 'Class Exercise',      'weight': Decimal('25.00'), 'order': 2},
        {'name': 'Homework/Assignment', 'weight': Decimal('15.00'), 'order': 3},
        {'name': 'Quiz',                'weight': Decimal('10.00'), 'order': 4},
    ]

    created = []
    for d in defaults:
        obj, _ = CAComponentType.objects.get_or_create(
            school=school,
            name=d['name'],
            defaults={
                'weight': d['weight'],
                'order': d['order'],
                'is_default': True,
                'is_active': True,
            }
        )
        created.append(obj)
    return created


def create_ca_component(school, classroom, subject, term, component_type, name, max_score, date, created_by, branch=None):
    """Creates a new CA component (e.g. Class Test 1)."""
    from apps.academics.models import CAComponent

    component = CAComponent.objects.create(
        school=school,
        branch=branch,
        classroom=classroom,
        subject=subject,
        term=term,
        component_type=component_type,
        name=name,
        max_score=max_score,
        date=date,
        created_by=created_by,
    )
    return component


def save_component_scores(school, component, score_data, entered_by):
    """
    Save scores for multiple students on a component.
    score_data: list of {'student_id': int, 'score': float, 'remarks': str}
    Returns list of CAComponentScore objects.
    """
    from apps.academics.models import CAComponentScore
    from apps.students.models import Student

    results = []
    errors = []

    with transaction.atomic():
        for item in score_data:
            student_id = item.get('student_id')
            score = Decimal(str(item.get('score', 0)))
            remarks = item.get('remarks', '')

            if score > component.max_score:
                errors.append(f"Score {score} exceeds max score {component.max_score} for student {student_id}.")
                continue

            if score < 0:
                errors.append(f"Score cannot be negative for student {student_id}.")
                continue

            obj, created = CAComponentScore.objects.get_or_create(
                student_id=student_id,
                component=component,
                defaults={
                    'school': school,
                    'score': score,
                    'remarks': remarks,
                    'entered_by': entered_by,
                }
            )

            if not created:
                if obj.locked:
                    errors.append(f"Score for student {student_id} is locked.")
                    continue
                obj.score = score
                obj.remarks = remarks
                obj.entered_by = entered_by
                obj.save()

            results.append(obj)

    return results, errors


def compute_class_score(school, student, subject, term):
    """
    Computes a student's class score (out of 30) from all component scores.
    Formula per component type:
        average_pct = mean(scores) / max_score * 100
        contribution = average_pct * (type_weight / 100) * 30 / 100
    Sums contributions across all types.
    """
    from apps.academics.models import CAComponent, CAComponentScore, CAComponentType

    component_types = CAComponentType.objects.filter(school=school, is_active=True)
    total_class_score = Decimal('0.00')

    for comp_type in component_types:
        # Get all components of this type for this subject/term
        components = CAComponent.objects.filter(
            school=school,
            subject=subject,
            term=term,
            component_type=comp_type,
        )

        if not components.exists():
            continue

        # Get student scores for these components
        scores = CAComponentScore.objects.filter(
            student=student,
            component__in=components,
            school=school,
        )

        if not scores.exists():
            continue

        # Compute average percentage across all components of this type
        total_pct = Decimal('0.00')
        count = 0
        for score_obj in scores:
            if score_obj.component.max_score > 0:
                pct = (score_obj.score / score_obj.component.max_score) * Decimal('100')
                total_pct += pct
                count += 1

        if count == 0:
            continue

        avg_pct = total_pct / count

        # Scale to contribution out of 30
        # contribution = avg_pct * (type_weight / 100) * 30 / 100
        contribution = avg_pct * (comp_type.weight / Decimal('100')) * Decimal('30') / Decimal('100')
        total_class_score += contribution

    # Cap at 30
    return min(total_class_score, Decimal('30.00'))


def update_ca_score(school, student, subject, term, classroom, branch=None):
    """
    Recomputes and saves the CAScore for a student/subject/term
    after component scores are entered.
    """
    from apps.academics.models import CAScore

    class_score = compute_class_score(school, student, subject, term)

    score_obj, _ = CAScore.objects.get_or_create(
        student=student,
        subject=subject,
        term=term,
        defaults={
            'school': school,
            'branch': branch,
            'classroom': classroom,
            'class_score': class_score,
            'exam_score': Decimal('0.00'),
        }
    )

    if not score_obj.locked:
        score_obj.class_score = class_score
        score_obj.save()

    return score_obj


def save_exam_score(school, student, subject, term, exam_score, classroom, branch=None):
    """Saves the end-of-term exam score for a student."""
    from apps.academics.models import CAScore

    if Decimal(str(exam_score)) > Decimal('70'):
        raise ValueError("Exam score cannot exceed 70.")

    score_obj, _ = CAScore.objects.get_or_create(
        student=student,
        subject=subject,
        term=term,
        defaults={
            'school': school,
            'branch': branch,
            'classroom': classroom,
            'class_score': Decimal('0.00'),
            'exam_score': Decimal(str(exam_score)),
        }
    )

    if score_obj.locked:
        raise ValueError("This score has been submitted and locked.")

    score_obj.exam_score = Decimal(str(exam_score))
    score_obj.save()
    return score_obj


def submit_ca_scores(school, classroom, subject, term, submitted_by, branch=None):
    """Locks all CA scores for a subject/term after final submission."""
    from apps.academics.models import CAScore
    from apps.students.models import Student

    students = Student.objects.filter(
        current_class=classroom,
        school=school,
        status='active',
    )

    scores = CAScore.objects.filter(
        student__in=students,
        subject=subject,
        term=term,
        school=school,
    )

    if not scores.exists():
        raise ValueError("No scores found to submit.")

    missing = students.count() - scores.count()
    if missing > 0:
        raise ValueError(f"{missing} student(s) still missing scores. Please complete all scores before submitting.")

    with transaction.atomic():
        now = timezone.now()
        scores.update(
            submitted=True,
            submitted_by=submitted_by,
            submitted_at=now,
            locked=True,
        )

    return scores