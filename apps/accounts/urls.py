from django.urls import path
from apps.accounts.views import (
    login_view,
    logout_view,
    password_reset_request,
    set_new_password,
    register_step1,
    register_step2,
    verify_phone,
    resend_otp,
    send_invite,
    staff_setup_account,
)

app_name = 'accounts'

urlpatterns = [
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('password-reset/', password_reset_request, name='password_reset'),
    path('password-reset/<str:token>/', set_new_password, name='set_new_password'),
    path('register/', register_step1, name='register_step1'),
    path('register/school/', register_step2, name='register_step2'),
    path('verify/phone/', verify_phone, name='verify_phone'),
    path('verify/phone/resend/', resend_otp, name='resend_otp'),
    path('staff/invite/<int:staff_pk>/', send_invite, name='send_staff_invite'),
    path('staff/setup/<uuid:token>/', staff_setup_account, name='staff_setup_account'),
]