from django.db import migrations


def set_teaches(apps, schema_editor):
    """
    Everyone who was already marked as teaching staff can teach. So can
    anyone holding a teacher role on SchoolMember, which catches staff
    registered before the category dropdown was required.
    """
    StaffProfile = apps.get_model('teachers', 'StaffProfile')
    SchoolMember = apps.get_model('tenants', 'SchoolMember')

    StaffProfile.objects.filter(staff_category='teaching').update(teaches=True)

    teacher_user_ids = SchoolMember.objects.filter(
        role='teacher', is_active=True, user__isnull=False
    ).values_list('user_id', flat=True)

    StaffProfile.objects.filter(
        user_id__in=list(teacher_user_ids)
    ).update(teaches=True)


def unset_teaches(apps, schema_editor):
    StaffProfile = apps.get_model('teachers', 'StaffProfile')
    StaffProfile.objects.update(teaches=False)


class Migration(migrations.Migration):

    dependencies = [
        ('teachers', '0003_staffprofile_teaches'),
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(set_teaches, unset_teaches),
    ]