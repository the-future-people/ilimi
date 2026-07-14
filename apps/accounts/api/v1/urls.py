from django.urls import path
from .views import (
    StartRegistrationView,
    ResendPendingOtpView,
    VerifyAndCreateView,
    CheckAvailabilityView,
    IlimiTokenObtainView,
    IlimiTokenRefreshView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
)

app_name = "auth-v1"

urlpatterns = [
    path("register/start/", StartRegistrationView.as_view(), name="register-start"),
    path("register/resend-otp/", ResendPendingOtpView.as_view(), name="register-resend-otp"),
    path("register/verify/", VerifyAndCreateView.as_view(), name="register-verify"),
    path("register/check-availability/", CheckAvailabilityView.as_view(), name="check-availability"),
    path("token/", IlimiTokenObtainView.as_view(), name="token-obtain"),
    path("token/refresh/", IlimiTokenRefreshView.as_view(), name="token-refresh"),
    path("password/reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
]