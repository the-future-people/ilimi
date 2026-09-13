from django.db import migrations


def set_ges(apps, schema_editor):
    """
    Every school that exists already follows GES.

    Everything built so far - the class ladder, the band split between
    class teachers and subject specialists, the three-term calendar and
    the lesson note format - is GES-shaped, and these schools have been
    running on it. New schools choose during setup and start blank.
    """
    School = apps.get_model('tenants', 'School')
    updated = School.objects.filter(curriculum='').update(curriculum='ges')
    print(f'\n  set {updated} existing schools to GES')


def clear(apps, schema_editor):
    School = apps.get_model('tenants', 'School')
    School.objects.filter(curriculum='ges').update(curriculum='')


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0014_alter_school_curriculum'),
    ]

    operations = [
        migrations.RunPython(set_ges, clear),
    ]