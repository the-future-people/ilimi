from rest_framework import serializers

from apps.classroom.models import Assignment, AssignmentCompletion


class AssignmentCompletionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = AssignmentCompletion
        fields = [
            'id', 'student', 'student_name', 'status', 'status_display',
            'submitted_file', 'submitted_at', 'marked_by', 'marked_at',
        ]


class AssignmentSerializer(serializers.ModelSerializer):
    """
    Full detail — used for both the teacher's own view and the parent's
    read-only view. completions is only meaningfully populated for the
    teacher (a full-class list); the parent-facing endpoint filters this
    down to just her own child before returning, in the view layer.
    """
    subject_name = serializers.CharField(source='subject_assignment.subject.name', read_only=True)
    classroom_name = serializers.CharField(source='subject_assignment.classroom.full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.full_name', read_only=True)
    completions = AssignmentCompletionSerializer(many=True, read_only=True)

    class Meta:
        model = Assignment
        fields = [
            'id', 'title', 'instructions', 'attachment', 'due_date',
            'allows_digital_submission',
            'subject_assignment', 'subject_name', 'classroom_name',
            'created_by', 'created_by_name',
            'completions', 'created_at',
        ]


class AssignmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = [
            'subject_assignment', 'title', 'instructions',
            'attachment', 'due_date', 'allows_digital_submission',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        school = self.context.get('school')
        if school is not None:
            from apps.academics.models import SubjectAssignment
            self.fields['subject_assignment'].queryset = SubjectAssignment.objects.filter(
                classroom__school=school
            )