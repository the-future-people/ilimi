from apps.notifications.models import Notification
from apps.tenants.models import SchoolMember


def create_notification(school, recipient, notification_type, title, message):
    """Create an in-app notification for a user."""
    return Notification.objects.create(
        school=school,
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
    )


def notify_admin_report_submitted(classroom, term, submitted_by):
    """
    Notify all school admins when a teacher submits report cards
    for evaluation. Creates in-app notification + sends SMS.
    """
    from apps.notifications.services.sms_service import send_sms

    school = classroom.school

    # Get all admin members for the school
    admins = SchoolMember.objects.filter(
        school=school,
        role='admin',
        is_active=True,
    ).select_related('user')

    teacher_name = f"{submitted_by.first_name} {submitted_by.last_name}".strip()
    title = "Report Cards Submitted for Evaluation"
    message = (
        f"{teacher_name} has submitted report cards for "
        f"{classroom} — {term} for your review."
    )

    for admin in admins:
        # In-app notification
        create_notification(
            school=school,
            recipient=admin.user,
            notification_type=Notification.TYPE_REPORT_SUBMITTED,
            title=title,
            message=message,
        )

        # SMS notification
        if admin.user.phone_number:
            sms_message = (
                f"Ilimi: {teacher_name} submitted report cards for "
                f"{classroom}, {term}. Please log in to review."
            )
            send_sms(phone_number=str(admin.user.phone_number), message=sms_message)


def notify_admin_report_released(classroom, term, released_by):
    """Notify admins when report cards are released to parents."""
    from apps.notifications.services.sms_service import send_sms

    school = classroom.school

    admins = SchoolMember.objects.filter(
        school=school,
        role='admin',
        is_active=True,
    ).select_related('user')

    title = "Report Cards Released to Parents"
    message = f"Report cards for {classroom} — {term} have been released to parents."

    for admin in admins:
        create_notification(
            school=school,
            recipient=admin.user,
            notification_type=Notification.TYPE_REPORT_RELEASED,
            title=title,
            message=message,
        )


def mark_notification_read(notification):
    notification.is_read = True
    notification.save()


def mark_all_read(user, school):
    Notification.objects.filter(
        recipient=user,
        school=school,
        is_read=False,
    ).update(is_read=True)


def get_unread_count(user, school):
    return Notification.objects.filter(
        recipient=user,
        school=school,
        is_read=False,
    ).count()

def mark_single_read(notification_id, user):
    """Mark a single notification as read."""
    try:
        notification = Notification.objects.get(id=notification_id, recipient=user)
        notification.is_read = True
        notification.save()
        return True
    except Notification.DoesNotExist:
        return False