from rest_framework import serializers

from apps.notifications.models import PaymentReminderRequest


class PaymentReminderRequestSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.user.full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.user.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = PaymentReminderRequest
        fields = [
            'id', 'student', 'student_name', 'student_fee', 'note',
            'status', 'status_display',
            'requested_by', 'requested_by_name',
            'reviewed_by', 'reviewed_by_name', 'reviewed_at',
            'decline_reason', 'message_sent', 'sent_at', 'created_at',
        ]
        read_only_fields = [
            'status', 'requested_by', 'reviewed_by', 'reviewed_at',
            'decline_reason', 'message_sent', 'sent_at',
        ]


class PaymentReminderRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentReminderRequest
        fields = ['student', 'student_fee', 'note']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        school = self.context.get('school')
        if school is not None:
            from apps.students.models import Student
            from apps.fees.models import StudentFee
            self.fields['student'].queryset = Student.objects.filter(school=school)
            self.fields['student_fee'].queryset = StudentFee.objects.filter(school=school)