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
        value = value.strip().replace(" ", "").replace("-", "")

        if value.startswith("0") and len(value) == 10:
            normalized = f"+233{value[1:]}"
        elif value.startswith("+233") and len(value) == 13:
            normalized = value
        elif value.startswith("233") and len(value) == 12:
            normalized = f"+{value}"
        else:
            raise serializers.ValidationError(
                "Enter a valid Ghana phone number, e.g. 0244558389."
            )

        if User.objects.filter(phone_number=normalized).exists():
            raise serializers.ValidationError(
                "An account with this phone number already exists."
            )

        return normalized

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


from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class IlimiTokenObtainSerializer(TokenObtainPairSerializer):
    username_field = "identifier"

    def validate(self, attrs):
        identifier = attrs.get("identifier", "").strip()
        password = attrs.get("password")

        if "@" in identifier:
            user = User.objects.filter(email=identifier.lower()).first()
        else:
            normalized = normalize_ghana_phone(identifier)
            user = User.objects.filter(phone_number=normalized).first() if normalized else None

        if user is None or not user.check_password(password):
            raise serializers.ValidationError(
                "Invalid email/phone number or password.", code="authorization"
            )

        if not user.is_active:
            raise serializers.ValidationError(
                "This account is inactive.", code="authorization"
            )

        refresh = self.get_token(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

        
def normalize_ghana_phone(value):
    value = value.strip().replace(" ", "").replace("-", "")
    if value.startswith("0") and len(value) == 10:
        return f"+233{value[1:]}"
    if value.startswith("+233") and len(value) == 13:
        return value
    if value.startswith("233") and len(value) == 12:
        return f"+{value}"
    if value.isdigit() and len(value) == 9:
        # Bare local number without leading 0, e.g. 551238710
        return f"+233{value}"
    return None


class StartRegistrationSerializer(serializers.Serializer):
    # Personal
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    position_title = serializers.ChoiceField(
        choices=['proprietor', 'head_teacher', 'administrator', 'other'],
        required=False, allow_blank=True, default=''
    )

    # School
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

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_phone_number(self, value):
        normalized = normalize_ghana_phone(value)
        if normalized is None:
            raise serializers.ValidationError("Enter a valid Ghana phone number, e.g. 0244558389.")
        if User.objects.filter(phone_number=normalized).exists():
            raise serializers.ValidationError("An account with this phone number already exists.")
        return normalized

    def validate_school_email(self, value):
        if not value:
            return value
        return value.lower().strip()

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("confirm_password"):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        try:
            validate_password(attrs["password"])
        except Exception as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        return attrs


class VerifyAndCreateSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    otp_code = serializers.CharField(min_length=4, max_length=8)

    def validate_phone_number(self, value):
        normalized = normalize_ghana_phone(value)
        return normalized or value.strip().replace(" ", "")