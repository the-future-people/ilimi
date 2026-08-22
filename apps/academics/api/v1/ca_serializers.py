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