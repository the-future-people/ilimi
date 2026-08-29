from django.db import migrations


def update_defaults(apps, schema_editor):
    """
    Give already-seeded administrators access to fees.

    In many Ghanaian schools there is no separate accounts office and the
    administrator takes payments and does the data entry, so the more
    common case becomes the default. Schools with an accounts office
    remove it.
    """
    SchoolRole = apps.get_model('tenants', 'SchoolRole')
    RolePermission = apps.get_model('tenants', 'RolePermission')

    added = 0
    for role in SchoolRole.objects.filter(slug='administrator'):
        _, created = RolePermission.objects.get_or_create(
            role=role,
            domain='fees',
            defaults={'level': 'full'},
        )
        if created:
            added += 1

    print(f'\n  gave fees to {added} administrators')


def noop(apps, schema_editor):
    """Removing the permission again is not worth restoring."""


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0011_populate_role_ref'),
    ]

    operations = [
        migrations.RunPython(update_defaults, noop),
    ]