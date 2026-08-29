"""
Default roles for a school.

The shape below is the structured Ghanaian school: a proprietor with
oversight, an assistant head running the day, an administrator on
registration, an accounts office on money, and academics over curriculum.

Schools that distribute the work differently — an administrator who also
collects fees, say — have their bundle adjusted after seeding rather than
being given a different set of roles.
"""
from apps.tenants.models import SchoolRole, RolePermission

VIEW = RolePermission.LEVEL_VIEW
REQUEST = RolePermission.LEVEL_REQUEST
FULL = RolePermission.LEVEL_FULL

DEFAULT_ROLES = [
    {
        'slug': 'proprietor',
        'name': 'Proprietor',
        'description': 'Owner. Oversight of the whole school, and acts on fees.',
        'permissions': {
            'students': VIEW,
            'admissions': VIEW,
            'staff': VIEW,
            'attendance': VIEW,
            'fees': FULL,
            'academics': VIEW,
            'communications': FULL,
            'documents': VIEW,
            'reports': VIEW,
            'parents': VIEW,
        },
    },
    {
        'slug': 'assistant_head',
        'name': 'Assistant Head Teacher',
        'description': 'Runs the school day to day. Oversees staff and academics.',
        'permissions': {
            'students': FULL,
            'admissions': FULL,
            'staff': FULL,
            'attendance': FULL,
            'fees': VIEW,
            'academics': FULL,
            'communications': FULL,
            'documents': FULL,
            'reports': FULL,
            'parents': FULL,
        },
    },
    {
        'slug': 'administrator',
        'name': 'Administrator',
        'description': 'Registers students and parents, issues documents and formalities.',
        'permissions': {
            'students': FULL,
            'admissions': FULL,
            'staff': VIEW,
            'attendance': VIEW,
            'communications': FULL,
            'documents': FULL,
            'reports': VIEW,
            'parents': FULL,
        },
    },
    {
        'slug': 'accounts',
        'name': 'Accounts Office',
        'description': 'Collects fees, issues receipts, reconciles.',
        'permissions': {
            'fees': FULL,
            'students': VIEW,
            'communications': REQUEST,
            'documents': VIEW,
            'reports': VIEW,
        },
    },
    {
        'slug': 'academics',
        'name': 'Head of Academics',
        'description': 'Curriculum, lesson plan vetting, academic oversight of teachers.',
        'permissions': {
            'academics': FULL,
            'students': VIEW,
            'staff': VIEW,
            'attendance': VIEW,
            'communications': REQUEST,
            'reports': VIEW,
        },
    },
    {
        'slug': 'teacher',
        'name': 'Teacher',
        'description': 'Their own classes: attendance, classwork, lesson notes.',
        'permissions': {},
    },
]


def seed_default_roles(school):
    """
    Create the default roles for a school if they are not already there.

    Safe to call more than once. Existing roles are left alone, so a
    school that has adjusted a bundle does not lose the change.
    """
    created = []

    for spec in DEFAULT_ROLES:
        role, was_created = SchoolRole.objects.get_or_create(
            school=school,
            slug=spec['slug'],
            defaults={
                'name': spec['name'],
                'description': spec['description'],
                'is_default': True,
            },
        )

        if not was_created:
            continue

        RolePermission.objects.bulk_create([
            RolePermission(role=role, domain=domain, level=level)
            for domain, level in spec['permissions'].items()
        ])
        created.append(role)

    return created