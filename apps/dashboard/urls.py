from django.urls import path
from apps.dashboard.views.home import dashboard_home
from apps.dashboard.views.staff import clear_staff_toast
from apps.dashboard.views.portals import (
    admin_portal,
    teacher_portal,
    teacher_classroom,
    teacher_class_detail,
    teacher_attendance,
    teacher_attendance_submit,
    teacher_ca_scores,
    teacher_ca_component_create,
    teacher_ca_scores_save,
    teacher_ca_exam_score_save,
    teacher_ca_scores_submit,
    accountant_portal,
    receptionist_portal,
)
from apps.dashboard.views.portals import (
    admin_portal,
    teacher_portal,
    teacher_classroom,
    teacher_class_detail,
    teacher_attendance,
    teacher_attendance_submit,
    accountant_portal,
    receptionist_portal,
)
from apps.dashboard.views.portals import (
    admin_portal,
    teacher_portal,
    teacher_classroom,
    teacher_class_detail,
    accountant_portal,
    receptionist_portal,
)
from apps.dashboard.views.portals import (
    admin_portal,
    teacher_portal,
    teacher_classroom,
    accountant_portal,
    receptionist_portal,
)
from apps.dashboard.views.portals import (
    admin_portal,
    teacher_classroom,
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
from apps.dashboard.views.staff import (
    staff_list,
    staff_register_step1,
    staff_register_step2,
    staff_register_step3,
    staff_register_step4,
    staff_register_step5,
    staff_register_step6,
    staff_register_review,
    staff_register_submit,
    staff_detail,
)
from apps.dashboard.views.portals import (
    admin_portal,
    teacher_portal,
    teacher_classroom,
    teacher_class_detail,
    teacher_attendance,
    teacher_attendance_submit,
    accountant_portal,
    receptionist_portal,
)
app_name = 'dashboard'

urlpatterns = [
    path('', dashboard_home, name='home'),
    path('admin/', admin_portal, name='admin_portal'),
    path('teacher/classroom/', teacher_classroom, name='teacher_classroom'),
    path('teacher/', teacher_portal, name='teacher_portal'),
    path('teacher/classroom/', teacher_classroom, name='teacher_classroom'),
    path('teacher/classroom/<int:classroom_id>/', teacher_class_detail, name='teacher_class_detail'),
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

        # ── Teachers & Staff ──────────────────────────────────────────────────────────
    path('admin/staff/', staff_list, name='staff_list'),
    path('admin/staff/register/step/1/', staff_register_step1, name='staff_register_step1'),
    path('admin/staff/register/step/2/', staff_register_step2, name='staff_register_step2'),
    path('admin/staff/register/step/3/', staff_register_step3, name='staff_register_step3'),
    path('admin/staff/register/step/4/', staff_register_step4, name='staff_register_step4'),
    path('admin/staff/register/step/5/', staff_register_step5, name='staff_register_step5'),
    path('admin/staff/register/step/6/', staff_register_step6, name='staff_register_step6'),
    path('admin/staff/register/review/', staff_register_review, name='staff_register_review'),
    path('admin/staff/register/submit/', staff_register_submit, name='staff_register_submit'),
    path('admin/staff/<int:pk>/', staff_detail, name='staff_detail'),
    path('admin/staff/clear-toast/', clear_staff_toast, name='clear_staff_toast'),
    path('teacher/classroom/<int:classroom_id>/attendance/', teacher_attendance, name='teacher_attendance'),
    path('teacher/classroom/<int:classroom_id>/attendance/submit/', teacher_attendance_submit, name='teacher_attendance_submit'),
    path('teacher/classroom/<int:classroom_id>/subject/<int:subject_id>/ca-scores/', teacher_ca_scores, name='teacher_ca_scores'),
    path('teacher/classroom/<int:classroom_id>/subject/<int:subject_id>/ca-scores/component/create/', teacher_ca_component_create, name='teacher_ca_component_create'),
    path('teacher/classroom/<int:classroom_id>/subject/<int:subject_id>/ca-scores/component/<int:component_id>/save/', teacher_ca_scores_save, name='teacher_ca_scores_save'),
    path('teacher/classroom/<int:classroom_id>/subject/<int:subject_id>/ca-scores/exam/<int:student_id>/save/', teacher_ca_exam_score_save, name='teacher_ca_exam_score_save'),
    path('teacher/classroom/<int:classroom_id>/subject/<int:subject_id>/ca-scores/submit/', teacher_ca_scores_submit, name='teacher_ca_scores_submit'),
]