from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from apps.tenants.services.onboarding import create_school_with_owner

User = get_user_model()


class RegisterStep1Serializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_phone_number(self, value):
        value = value.strip().replace(" ", "")
        if not value.startswith("+"):
            raise serializers.ValidationError(
                "Phone number must include the country code, e.g. +233XXXXXXXXX"
            )
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("confirm_password"):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        try:
            validate_password(attrs["password"])
        except Exception as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        return attrs


class RegisterSchoolSerializer(serializers.Serializer):
    school_name = serializers.CharField(max_length=255)
    school_email = serializers.EmailField(required=False, allow_blank=True, default='')
    school_phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    city = serializers.CharField(max_length=100)
    country = serializers.CharField(max_length=100, default="Ghana")
    school_type = serializers.ChoiceField(
        choices=['basic', 'shs', 'international', 'group'],
        required=False, allow_blank=True, default=''
    )
    expected_student_count = serializers.ChoiceField(
        choices=['under_100', '100_300', '300_600', '600_plus'],
        required=False, allow_blank=True, default=''
    )
    position_title = serializers.ChoiceField(
        choices=['proprietor', 'head_teacher', 'administrator', 'other'],
        required=False, allow_blank=True, default=''
    )

    def validate_phone_number(self, value):
        value = value.strip().replace(" ", "")
        if not User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("No account found with this phone number.")
        return value

    def validate_school_email(self, value):
        return value.lower().strip()

class OTPVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    otp_code = serializers.CharField(min_length=4, max_length=8)

    def validate_phone_number(self, value):
        return value.strip().replace(" ", "")


class OTPResendSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)

    def validate_phone_number(self, value):
        value = value.strip().replace(" ", "")
        if not User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("No account found with this phone number.")
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower().strip()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs.pop("confirm_password"):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        try:
            validate_password(attrs["new_password"])
        except Exception as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "is_email_verified",
            "is_phone_verified",
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.user.get_full_name()