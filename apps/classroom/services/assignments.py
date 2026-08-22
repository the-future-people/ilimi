"""
Assignment creation and completion-tracking logic. Creating an assignment
auto-populates one AssignmentCompletion row per active student in the
classroom, so a teacher's checklist is ready immediately — she's marking
existing rows, not building the list herself.
"""

from apps.classroom.models import Assignment, AssignmentCompletion
from apps.students.models import Student


def create_assignment(subject_assignment, created_by, title, instructions,
                       due_date=None, attachment=None, allows_digital_submission=False):
    assignment = Assignment.objects.create(
        subject_assignment=subject_assignment,
        created_by=created_by,
        title=title,
        instructions=instructions,
        due_date=due_date,
        attachment=attachment,
        allows_digital_submission=allows_digital_submission,
    )

    students = Student.objects.filter(
        current_class=subject_assignment.classroom, status='active'
    )
    AssignmentCompletion.objects.bulk_create([
        AssignmentCompletion(assignment=assignment, student=student)
        for student in students
    ])

    return assignment


def mark_completion(completion, status, marked_by):
    """Checklist track — a teacher marks done/not-done for physical work."""
    from django.utils import timezone
    completion.status = status
    completion.marked_by = marked_by
    completion.marked_at = timezone.now()
    completion.save()
    return completion


def submit_completion(completion, submitted_file):
    """Digital track — a file gets attached, submitted by a parent on the
    child's behalf (no student-login concept exists yet)."""
    from django.utils import timezone
    completion.submitted_file = submitted_file
    completion.status = 'submitted'
    completion.submitted_at = timezone.now()
    completion.save()
    return completion