from django.utils import timezone
from apps.academics.models import CAScore, SubjectAssignment
from apps.students.models import Student
from apps.reports.models import ReportCard, ReportCardEntry, ReportCardRemark


def generate_report_cards(classroom, term, generated_by):
    """
    Generate draft report cards for all students in a classroom for a given term.
    Snapshots all locked CAScore records into ReportCardEntry rows.
    Skips students who already have a report card for this classroom/term.
    """
    school = classroom.school
    branch = classroom.branch

    students = Student.objects.filter(
        school=school,
        current_class=classroom,
        status='active'
    )

    generated = []

    for student in students:
        report_card, created = ReportCard.objects.get_or_create(
                    student=student,
                    classroom=classroom,
                    term=term,
                    defaults={
                        'school': school,
                        'branch': branch or student.branch,
                        'generated_by': generated_by,
                        'status': ReportCard.STATUS_DRAFT,
                    }
                )

        if not created:
                    continue

        # Snapshot all CA scores for this student in this term
        ca_scores = CAScore.objects.filter(
            school=school,
            student=student,
            term=term,
            locked=True,
        )

        for ca in ca_scores:
            ReportCardEntry.objects.get_or_create(
                report_card=report_card,
                subject=ca.subject,
                defaults={
                    'class_score': ca.class_score,
                    'exam_score': ca.exam_score,
                    'total': ca.total,
                    'grade': ca.grade,
                }
            )

        # Create blank remark for form teacher to fill
        ReportCardRemark.objects.get_or_create(
            report_card=report_card,
            defaults={'teacher': generated_by}
        )

        generated.append(report_card)

    return generated


def save_remark(report_card, remark_text, teacher):
    """Save or update the form teacher's remark for a student's report card."""
    remark, _ = ReportCardRemark.objects.get_or_create(
        report_card=report_card,
        defaults={'teacher': teacher}
    )
    remark.remark = remark_text
    remark.teacher = teacher
    remark.save()
    return remark


def submit_report_cards(classroom, term):
    """
    Submit all draft report cards for a classroom/term for admin evaluation.
    Only submits cards that have a remark filled in.
    """
    report_cards = ReportCard.objects.filter(
        classroom=classroom,
        term=term,
        status=ReportCard.STATUS_DRAFT,
    )

    submitted = []
    for rc in report_cards:
        rc.status = ReportCard.STATUS_SUBMITTED
        rc.save()
        submitted.append(rc)

    return submitted


def approve_report_card(report_card, approved_by, head_comment):
    """Admin approves a single report card and adds head's comment."""
    report_card.status = ReportCard.STATUS_APPROVED
    report_card.approved_by = approved_by
    report_card.approved_at = timezone.now()
    report_card.head_comment = head_comment
    report_card.save()
    return report_card


def release_report_cards(classroom, term):
    """Release all approved report cards for a classroom/term to parents."""
    report_cards = ReportCard.objects.filter(
        classroom=classroom,
        term=term,
        status=ReportCard.STATUS_APPROVED,
    )

    released = []
    for rc in report_cards:
        rc.status = ReportCard.STATUS_RELEASED
        rc.released_at = timezone.now()
        rc.save()
        released.append(rc)

    return released