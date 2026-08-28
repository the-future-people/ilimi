from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from drf_spectacular.utils import extend_schema

from apps.accounts.services.handles import normalise_username
from apps.core.phone import is_valid_phone, normalise_phone
from apps.core.renderers import IlimiAPIRenderer
from apps.accounts.models import PendingRegistration
from apps.accounts.services.registration import start_registration, resend_pending_otp, verify_and_create

from .serializers import (
    StartRegistrationSerializer,
    VerifyAndCreateSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    UserProfileSerializer,
    IlimiTokenObtainSerializer,
    )
from apps.core.phone import normalise_phone, is_valid_phone
from apps.accounts.services.handles import normalise_username

User = get_user_model()

from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.services.password_reset import (
    request_reset,
    verify_code,
    complete_reset,
)


def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


@extend_schema(tags=["Auth"])
class StartRegistrationView(GenericAPIView):
    serializer_class = StartRegistrationSerializer
    permission_classes = [AllowAny]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pending = start_registration(serializer.validated_data)

        return Response(
            {
                "message": "Verification code sent to your phone.",
                "phone_number": pending.phone_number,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Auth"])
class ResendPendingOtpView(GenericAPIView):
    permission_classes = [AllowAny]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, *args, **kwargs):
        phone_number = request.data.get("phone_number", "").strip()
        pending = PendingRegistration.objects.filter(phone_number=phone_number).first()

        if not pending:
            return Response(
                {"message": "No pending registration found for this phone number."},
                status=status.HTTP_404_NOT_FOUND,
            )

        success, message = resend_pending_otp(pending)
        if not success:
            return Response({"message": message}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        return Response({"message": message}, status=status.HTTP_200_OK)


@extend_schema(tags=["Auth"])
class VerifyAndCreateView(GenericAPIView):
    serializer_class = VerifyAndCreateSerializer
    permission_classes = [AllowAny]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data["phone_number"]
        otp_code = serializer.validated_data["otp_code"]

        pending = PendingRegistration.objects.filter(phone_number=phone_number).first()
        if not pending:
            return Response(
                {"message": "No pending registration found. Please start again."},
                status=status.HTTP_404_NOT_FOUND,
            )

        success, message, user = verify_and_create(pending, otp_code)
        if not success:
            return Response({"message": message}, status=status.HTTP_400_BAD_REQUEST)

        tokens = _tokens_for_user(user)
        profile = UserProfileSerializer(user).data

        return Response(
            {
                "message": "Welcome to Ilimi!",
                "tokens": tokens,
                "user": profile,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Auth"])
class IlimiTokenObtainView(TokenObtainPairView):
    serializer_class = IlimiTokenObtainSerializer
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            identifier = request.data.get("identifier", "").strip()
            user = None
            if "@" in identifier[1:]:
                user = User.objects.filter(email=identifier.lower()).first()
            else:
                normalized = normalise_phone(identifier)
                if normalized.startswith("+"):
                    user = User.objects.filter(phone_number=normalized).first()
                if user is None:
                    user = User.objects.filter(
                        username=normalise_username(identifier)
                    ).first()

            if user:
                response.data["user"] = UserProfileSerializer(user).data
                response.data["message"] = f"Welcome back, {user.first_name}!"
        return response


@extend_schema(tags=["Auth"])
class IlimiTokenRefreshView(TokenRefreshView):
    renderer_classes = [IlimiAPIRenderer]


@extend_schema(tags=["Auth"])
class PasswordResetStartView(GenericAPIView):
    """Public. Sends a code to a registered phone."""

    permission_classes = [AllowAny]
    renderer_classes = [IlimiAPIRenderer]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        ok, message = request_reset(request.data.get('phone_number', ''))
        return Response({'message': message}, status=200 if ok else 400)


@extend_schema(tags=["Auth"])
class PasswordResetVerifyView(GenericAPIView):
    """Public. Exchanges a code for a short-lived ticket."""

    permission_classes = [AllowAny]
    renderer_classes = [IlimiAPIRenderer]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        ok, message, ticket = verify_code(
            request.data.get('phone_number', ''),
            request.data.get('code', ''),
        )
        if not ok:
            return Response({'message': message}, status=400)
        return Response({'message': message, 'ticket': ticket})


@extend_schema(tags=["Auth"])
class PasswordResetCompleteView(GenericAPIView):
    """Public. Sets the new password and signs them in."""

    permission_classes = [AllowAny]
    renderer_classes = [IlimiAPIRenderer]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        password = request.data.get('new_password', '')
        confirm = request.data.get('confirm_password', '')

        if len(password) < 8:
            return Response({'message': 'Your password needs at least 8 characters.'}, status=400)
        if password != confirm:
            return Response({'message': 'The two passwords do not match.'}, status=400)

        ok, message, user = complete_reset(request.data.get('ticket', ''), password)
        if not ok:
            return Response({'message': message}, status=400)

        refresh = RefreshToken.for_user(user)
        return Response({
            'message': message,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


@extend_schema(tags=["Auth"])
class _RemovedPasswordResetRequestView(GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email=email).first()
        if user and user.is_active:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            # TODO: send via notifications backend
        return Response(
            {"message": "If that email is registered, you'll receive a reset link shortly."},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Auth"])
class PasswordResetConfirmView(GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            pk = force_str(urlsafe_base64_decode(serializer.validated_data["uid"]))
            user = User.objects.get(pk=pk)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response(
                {"status": "error", "message": "Invalid or expired reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not default_token_generator.check_token(user, serializer.validated_data["token"]):
            return Response(
                {"status": "error", "message": "Invalid or expired reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response(
            {"message": "Password updated successfully. You can now log in."},
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Auth"])
class CheckAvailabilityView(GenericAPIView):
    permission_classes = [AllowAny]
    renderer_classes = [IlimiAPIRenderer]

    def post(self, request, *args, **kwargs):
        field = request.data.get("field")
        value = request.data.get("value", "").strip()

        if not value:
            return Response({"available": True})

        if field == "email":
            exists = User.objects.filter(email=value.lower()).exists()
        elif field == "phone_number":
            if not is_valid_phone(value):
                return Response({"available": False, "message": "Please enter a valid Ghana phone number (e.g. 0244558389 or 244558389)."})
            exists = User.objects.filter(phone_number=normalise_phone(value)).exists()
        elif field == "school_email":
            from apps.tenants.models import School
            exists = School.objects.filter(email=value.lower()).exists()
        else:
            return Response({"message": "Unknown field."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "available": not exists,
            "message": None if not exists else "This is already in use.",
        })