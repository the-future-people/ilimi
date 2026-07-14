from django.urls import path
from apps.accounts.views import (
    login_view,
    logout_view,
    password_reset_request,
    set_new_password,
    send_invite,
    staff_setup_account,
)

app_name = 'accounts'

urlpatterns = [
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('password-reset/', password_reset_request, name='password_reset'),
    path('password-reset/<str:token>/', set_new_password, name='set_new_password'),
    path('staff/invite/<int:staff_pk>/', send_invite, name='send_staff_invite'),
    path('staff/setup/<uuid:token>/', staff_setup_account, name='staff_setup_account'),
]