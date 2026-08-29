from django.db import migrations

# Old string role -> new role slug.
#
# school_admin becomes assistant_head rather than proprietor: these are
# operational accounts running schools today, and Proprietor is deliberately
# oversight-only. A genuine owner is moved to proprietor by hand when their
# school is set up.
ROLE_MAP = {
    'school_admin': 'assistant_head',
    'branch_manager': 'assistant_head',
    'registrar': 'administrator',
    'accountant': 'accounts',
    'head_of_academics': 'academics',
    'teacher': 'teacher',
}


def populate(apps, schema_editor):
    from apps.tenants.services.roles import DEFAULT_ROLES

    School = apps.get_model('tenants', 'School')
    SchoolRole = apps.get_model('tenants', 'SchoolRole')
    RolePermission = apps.get_model('tenants', 'RolePermission')
    SchoolMember = apps.get_model('tenants', 'SchoolMember')

    # Seed roles for every school. Written out rather than calling the
    # service, because a migration must not depend on today's model
    # classes — only on the historical ones above.
    for school in School.objects.all():
        for spec in DEFAULT_ROLES:
            role, created = SchoolRole.objects.get_or_create(
                school=school,
                slug=spec['slug'],
                defaults={
                    'name': spec['name'],
                    'description': spec['description'],
                    'is_default': True,
                },
            )
            if created and spec['permissions']:
                RolePermission.objects.bulk_create([
                    RolePermission(role=role, domain=domain, level=level)
                    for domain, level in spec['permissions'].items()
                ])

    # Map each member across.
    unmapped = []
    for member in SchoolMember.objects.select_related('school').all():
        slug = ROLE_MAP.get(member.role)
        if not slug:
            unmapped.append(f'member {member.pk}: role {member.role!r}')
            continue

        role = SchoolRole.objects.filter(
            school_id=member.school_id, slug=slug
        ).first()
        if not role:
            unmapped.append(f'member {member.pk}: no {slug} at school {member.school_id}')
            continue

        member.role_ref = role
        member.save(update_fields=['role_ref'])

    if unmapped:
        print('\nMembers left without a role:')
        for line in unmapped:
            print('  ' + line)


def unpopulate(apps, schema_editor):
    SchoolMember = apps.get_model('tenants', 'SchoolMember')
    SchoolMember.objects.update(role_ref=None)


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0010_schoolmember_role_ref'),
    ]

    operations = [
        migrations.RunPython(populate, unpopulate),
    ]