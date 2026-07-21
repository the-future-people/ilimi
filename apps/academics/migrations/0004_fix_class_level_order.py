from django.db import migrations


def recalculate_orders(apps, schema_editor):
    ClassLevel = apps.get_model('academics', 'ClassLevel')
    # Historical models have no LEVEL_ORDER attribute, so the mapping is
    # repeated here deliberately — migrations must not depend on current
    # model code, which is free to change after this migration is applied.
    order_map = {
        'nursery_1': 0, 'nursery_2': 1,
        'kindergarten_1': 2, 'kindergarten_2': 3,
        'primary_1': 4, 'primary_2': 5, 'primary_3': 6,
        'primary_4': 7, 'primary_5': 8, 'primary_6': 9,
        'jhs_1': 10, 'jhs_2': 11, 'jhs_3': 12,
        'shs_1': 13, 'shs_2': 14, 'shs_3': 15,
        'other': 999,
    }
    for level in ClassLevel.objects.all():
        level.order = order_map.get(level.name, 999)
        level.save(update_fields=['order'])


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0003_gescalendartemplate_gescalendartermtemplate'),
    ]

    operations = [
        migrations.RunPython(recalculate_orders, migrations.RunPython.noop),
    ]