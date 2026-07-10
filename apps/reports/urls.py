from django.urls import path
from apps.reports.views.teacher_reports import (
    teacher_report_generate,
    teacher_report_student_list,
    teacher_report_preview,
    teacher_report_save_remark,
    teacher_report_submit,
)
from apps.reports.views.admin_reports import (
    admin_report_queue,
    admin_report_class_review,
    admin_report_student_review,
    admin_report_approve,
    admin_report_release,
    admin_notifications_mark_read,
)

urlpatterns = [
    # ── Teacher ──────────────────────────────────────────────────────────
    path(
        'classroom/<int:classroom_id>/term/<int:term_id>/generate/',
        teacher_report_generate,
        name='teacher_report_generate',
    ),
    path(
        'classroom/<int:classroom_id>/term/<int:term_id>/students/',
        teacher_report_student_list,
        name='teacher_report_student_list',
    ),
    path(
        'preview/<int:report_card_id>/',
        teacher_report_preview,
        name='teacher_report_preview',
    ),
    path(
        'preview/<int:report_card_id>/save-remark/',
        teacher_report_save_remark,
        name='teacher_report_save_remark',
    ),
    path(
        'classroom/<int:classroom_id>/term/<int:term_id>/submit/',
        teacher_report_submit,
        name='teacher_report_submit',
    ),

    # ── Admin ─────────────────────────────────────────────────────────────
    path(
        'admin/queue/',
        admin_report_queue,
        name='admin_report_queue',
    ),
    path(
        'admin/classroom/<int:classroom_id>/term/<int:term_id>/review/',
        admin_report_class_review,
        name='admin_report_class_review',
    ),
    path(
        'admin/report/<int:report_card_id>/review/',
        admin_report_student_review,
        name='admin_report_student_review',
    ),
    path(
        'admin/report/<int:report_card_id>/approve/',
        admin_report_approve,
        name='admin_report_approve',
    ),
    path(
        'admin/classroom/<int:classroom_id>/term/<int:term_id>/release/',
        admin_report_release,
        name='admin_report_release',
    ),
    path(
        'admin/notifications/mark-read/',
        admin_notifications_mark_read,
        name='admin_notifications_mark_read',
    ),
]