from django.urls import path
from apps.dashboard.views.home import dashboard_home
from apps.dashboard.views.portals import (
    admin_portal,
    teacher_portal,
    accountant_portal,
    receptionist_portal,
)
from apps.dashboard.views.students import (
    student_list,
    student_enrol_step1,
    student_enrol_step2,
    student_enrol_step3,
    student_enrol_step4,
    student_enrol_step5,
    student_enrol_step6,
    student_enrol_submit,
    student_detail,
)

app_name = 'dashboard'

urlpatterns = [
    path('', dashboard_home, name='home'),
    path('admin/', admin_portal, name='admin_portal'),
    path('teacher/', teacher_portal, name='teacher_portal'),
    path('accountant/', accountant_portal, name='accountant_portal'),
    path('receptionist/', receptionist_portal, name='receptionist_portal'),

    # ── Students & Admissions ─────────────────────────────────────────
    path('admin/students/', student_list, name='student_list'),
    path('admin/students/enrol/step/1/', student_enrol_step1, name='student_enrol_step1'),
    path('admin/students/enrol/step/2/', student_enrol_step2, name='student_enrol_step2'),
    path('admin/students/enrol/step/3/', student_enrol_step3, name='student_enrol_step3'),
    path('admin/students/enrol/step/4/', student_enrol_step4, name='student_enrol_step4'),
    path('admin/students/enrol/step/5/', student_enrol_step5, name='student_enrol_step5'),
    path('admin/students/enrol/step/6/', student_enrol_step6, name='student_enrol_step6'),
    path('admin/students/enrol/submit/', student_enrol_submit, name='student_enrol_submit'),
    path('admin/students/<int:pk>/', student_detail, name='student_detail'),
]