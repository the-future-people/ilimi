from rest_framework import serializers
from apps.academics.models import (
    AcademicYear, Term, ClassLevel, ClassRoom, Subject, SubjectAssignment
)
from apps.tenants.models import SchoolMember
from apps.tenants.models import SchoolMember, Branch
from apps.academics.services.setup import get_or_create_class_level


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ['id', 'name', 'start_date', 'end_date', 'is_current']


class AcademicYearCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ['name', 'start_date', 'end_date', 'is_current']

    def validate_name(self, value):
        school = self.context['school']
        if AcademicYear.objects.filter(school=school, name=value).exists():
            raise serializers.ValidationError(
                f"An academic year named '{value}' already exists for this school."
            )
        return value


class TermSerializer(serializers.ModelSerializer):
    name_display = serializers.CharField(source='get_name_display', read_only=True)

    class Meta:
        model = Term
        fields = ['id', 'name', 'name_display', 'start_date', 'end_date', 'is_current']


class TermCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Term
        fields = ['name', 'start_date', 'end_date', 'is_current']

    def validate_name(self, value):
        academic_year = self.context['academic_year']
        if Term.objects.filter(academic_year=academic_year, name=value).exists():
            raise serializers.ValidationError(
                f"'{value}' already exists for this academic year."
            )
        return value


class ClassLevelSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = ClassLevel
        fields = ['id', 'name', 'display_name', 'custom_name', 'order', 'is_active']


class ClassLevelCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassLevel
        fields = ['name', 'custom_name', 'order', 'is_active']

    def validate_name(self, value):
        school = self.context['school']
        if ClassLevel.objects.filter(school=school, name=value).exists():
            raise serializers.ValidationError(
                f"Class level '{value}' already exists for this school."
            )
        return value


class ClassRoomSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    class_level_display = serializers.CharField(
        source='class_level.display_name', read_only=True
    )
    form_teacher_name = serializers.SerializerMethodField()
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = ClassRoom
        fields = [
            'id', 'full_name', 'class_level', 'class_level_display',
            'section_name', 'elective_group', 'form_teacher',
            'form_teacher_name', 'branch', 'branch_name',
            'capacity', 'is_active',
        ]

    def get_form_teacher_name(self, obj):
        if obj.form_teacher:
            return obj.form_teacher.user.full_name
        return None


class ClassRoomCreateSerializer(serializers.ModelSerializer):
    """
    Accepts either an existing class_level PK or a class_level_name from
    ClassLevel.LEVEL_CHOICES, which is get-or-created for the school.

    The name path is what the Classes tab uses: a school picks 'JHS 1' from
    a dropdown and the ClassLevel is created behind the scenes, so creating
    a class is one action rather than two.
    """

    class_level = serializers.PrimaryKeyRelatedField(
        queryset=ClassLevel.objects.all(), required=False
    )
    class_level_name = serializers.ChoiceField(
        choices=ClassLevel.LEVEL_CHOICES, required=False, write_only=True
    )

    class Meta:
        model = ClassRoom
        fields = [
            'class_level', 'class_level_name', 'section_name',
            'elective_group', 'form_teacher', 'branch',
            'capacity', 'is_active',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        school = self.context.get('school')
        if school is not None:
            # Scope relations to the school — without this a caller can
            # reference another tenant's level, teacher or branch by id.
            self.fields['class_level'].queryset = ClassLevel.objects.filter(
                school=school
            )
            self.fields['form_teacher'].queryset = SchoolMember.objects.filter(
                school=school, is_active=True
            )
            self.fields['branch'].queryset = Branch.objects.filter(school=school)

    def validate(self, attrs):
        school = self.context['school']
        academic_year = self.context['academic_year']

        class_level = attrs.get('class_level')
        level_name = attrs.pop('class_level_name', None)

        if class_level is None:
            if level_name is None:
                if self.instance:
                    class_level = self.instance.class_level
                else:
                    raise serializers.ValidationError({
                        'class_level': 'Provide either class_level or class_level_name.'
                    })
            else:
                class_level = get_or_create_class_level(school, level_name)
                attrs['class_level'] = class_level

        section_name = attrs.get('section_name', '')
        if not section_name and self.instance:
            section_name = self.instance.section_name

        qs = ClassRoom.objects.filter(
            school=school,
            academic_year=academic_year,
            class_level=class_level,
            section_name=section_name,
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                f"A classroom '{class_level.display_name} {section_name}' "
                f"already exists for this academic year."
            )
        return attrs


class SubjectSerializer(serializers.ModelSerializer):
    subject_type_display = serializers.CharField(
        source='get_subject_type_display', read_only=True
    )

    class Meta:
        model = Subject
        fields = [
            'id', 'name', 'code', 'subject_type',
            'subject_type_display', 'elective_group', 'is_active',
        ]


class SubjectCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['name', 'code', 'subject_type', 'elective_group', 'is_active']

    def validate_name(self, value):
        school = self.context['school']
        qs = Subject.objects.filter(school=school, name=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                f"A subject named '{value}' already exists for this school."
            )
        return value


class SubjectAssignmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    classroom_name = serializers.CharField(source='classroom.full_name', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    term_display = serializers.CharField(source='term.get_name_display', read_only=True)

    class Meta:
        model = SubjectAssignment
        fields = [
            'id', 'subject', 'subject_name', 'classroom', 'classroom_name',
            'teacher', 'teacher_name', 'term', 'term_display', 'periods_per_week',
        ]

    def get_teacher_name(self, obj):
        if obj.teacher:
            return obj.teacher.user.full_name
        return None


class SubjectAssignmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubjectAssignment
        fields = ['subject', 'classroom', 'teacher', 'term', 'periods_per_week']

    def validate(self, attrs):
        classroom = attrs.get('classroom')
        subject = attrs.get('subject')
        term = attrs.get('term')

        qs = SubjectAssignment.objects.filter(
            classroom=classroom, subject=subject, term=term
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "This subject is already assigned to this classroom for this term."
            )
        return attrs

