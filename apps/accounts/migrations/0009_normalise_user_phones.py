from django.db import migrations


def normalise(apps, schema_editor):
    """
    Bring every stored phone number to canonical E.164.

    Numbers were saved in whatever format was typed, so '0241718191' and
    '+233241234567' could both exist. Login normalises before lookup, so
    anything not canonical could not be used to sign in.
    """
    from apps.core.phone import normalise_phone

    User = apps.get_model('accounts', 'User')

    seen = {}
    conflicts = []

    rows = User.objects.exclude(phone_number__isnull=True).exclude(phone_number='')
    for user in rows.order_by('id'):
        canonical = normalise_phone(user.phone_number)
        if not canonical.startswith('+'):
            # Unparseable. Leave it alone rather than guess.
            continue

        if canonical in seen:
            conflicts.append(
                f'{canonical}: user {seen[canonical]} and user {user.pk}'
            )
            continue

        seen[canonical] = user.pk
        if user.phone_number != canonical:
            user.phone_number = canonical
            user.save(update_fields=['phone_number'])

    if conflicts:
        raise RuntimeError(
            'Two accounts share a phone number once normalised. Resolve '
            'these by hand, then re-run:\n  ' + '\n  '.join(conflicts)
        )


def noop(apps, schema_editor):
    """Original formats are not recoverable, and canonical is correct."""


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_user_username'),
    ]

    operations = [
        migrations.RunPython(normalise, noop),
    ]