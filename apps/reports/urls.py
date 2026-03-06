from django.urls import path
from apps.reports.views.teacher_reports import (
    teacher_report_generate,
    teacher_report_student_list,
    teacher_report_preview,
    teacher_report_save_remark,
    teacher_report_submit,
)

urlpatterns = [
    # Generate report cards for a classroom/term
    path(
        'classroom/<int:classroom_id>/term/<int:term_id>/generate/',
        teacher_report_generate,
        name='teacher_report_generate',
    ),
    # List all students' report cards
    path(
        'classroom/<int:classroom_id>/term/<int:term_id>/students/',
        teacher_report_student_list,
        name='teacher_report_student_list',
    ),
    # Preview a single student's report card
    path(
        'preview/<int:report_card_id>/',
        teacher_report_preview,
        name='teacher_report_preview',
    ),
    # Save teacher remark
    path(
        'preview/<int:report_card_id>/save-remark/',
        teacher_report_save_remark,
        name='teacher_report_save_remark',
    ),
    # Submit all report cards for admin evaluation
    path(
        'classroom/<int:classroom_id>/term/<int:term_id>/submit/',
        teacher_report_submit,
        name='teacher_report_submit',
    ),
]