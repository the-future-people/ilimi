from rest_framework import serializers
from apps.academics.models import (
    CAComponentType, Classwork, ClassworkRecord, CAScore
)


class CAComponentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CAComponentType
        fields = ['id', 'name', 'weight', 'is_active', 'is_default', 'order']


class ClassworkSerializer(serializers.ModelSerializer):
    component_type_name = serializers.CharField(source='component_type.name', read_only=True)

    class Meta:
        model = Classwork
        fields = [
            'id', 'classroom', 'subject', 'term', 'component_type',
            'component_type_name', 'name', 'max_score', 'date',
        ]


class ClassworkCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classwork
        fields = [
            'classroom', 'subject', 'term', 'component_type',
            'name', 'max_score', 'date',
        ]


class ClassworkRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    component = serializers.PrimaryKeyRelatedField(source='classwork', read_only=True)

    class Meta:
        model = ClassworkRecord
        fields = ['id', 'student', 'student_name', 'component', 'score', 'remarks', 'locked']

class ClassworkFullSerializer(serializers.ModelSerializer):
    """Full Classwork shape for the teacher's Classwork panel."""

    component_type_name = serializers.CharField(source='component_type.name', read_only=True)
    component_weight    = serializers.DecimalField(
        source='component_type.weight', max_digits=5, decimal_places=2, read_only=True
    )
    work_type_display   = serializers.CharField(source='get_work_type_display', read_only=True)
    subject_name        = serializers.CharField(source='subject.name', read_only=True)
    is_graded           = serializers.BooleanField(read_only=True)

    record_count   = serializers.SerializerMethodField()
    unmarked_count = serializers.SerializerMethodField()

    class Meta:
        model = Classwork
        fields = [
            'id', 'classroom', 'subject', 'subject_name', 'term',
            'work_type', 'work_type_display',
            'component_type', 'component_type_name', 'component_weight', 'is_graded',
            'name', 'instructions', 'attachment',
            'max_score', 'date', 'due_date',
            'visible_to_parents', 'allows_digital_submission',
            'record_count', 'unmarked_count',
            'created_at',
        ]

    def get_record_count(self, obj):
        return obj.records.count()

    def get_unmarked_count(self, obj):
        return obj.records.filter(status='not_done').count()


class ClassworkCreateFullSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classwork
        fields = [
            'classroom', 'subject', 'term',
            'work_type', 'component_type',
            'name', 'instructions', 'attachment',
            'max_score', 'date', 'due_date',
            'visible_to_parents', 'allows_digital_submission',
        ]

    def validate(self, attrs):
        component_type = attrs.get('component_type')
        max_score = attrs.get('max_score')

        if component_type and not max_score:
            raise serializers.ValidationError({
                'max_score': 'Graded work needs a maximum score.'
            })

        due_date = attrs.get('due_date')
        date = attrs.get('date')
        if due_date and date and due_date < date:
            raise serializers.ValidationError({
                'due_date': 'Due date cannot be before the date the work was set.'
            })

        return attrs


class ClassworkRecordFullSerializer(serializers.ModelSerializer):
    """One student's record, for the marking screen."""

    student_name  = serializers.CharField(source='student.full_name', read_only=True)
    student_photo = serializers.ImageField(source='student.photo', read_only=True)
    submission_count = serializers.SerializerMethodField()

    class Meta:
        model = ClassworkRecord
        fields = [
            'id', 'student', 'student_name', 'student_photo',
            'status', 'score', 'remarks',
            'submitted_file', 'submitted_at', 'submission_count',
            'marked_at', 'locked',
        ]

    def get_submission_count(self, obj):
        return obj.submissions.count()

class CAScoreSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)

    class Meta:
        model = CAScore
        fields = [
            'id', 'student', 'student_name', 'subject', 'term',
            'class_score', 'exam_score', 'total', 'grade',
            'submitted', 'locked',
        ]


# Backward-compatible aliases — remove once views are updated.
CAComponentSerializer = ClassworkSerializer
CAComponentCreateSerializer = ClassworkCreateSerializer
CAComponentScoreSerializer = ClassworkRecordSerializer