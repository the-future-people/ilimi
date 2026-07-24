"""
Single source of truth for role -> domain permissions.

Mirrored in the frontend at src/constants/permissions.js — keep both in
sync by hand; each file comments a pointer to the other. A small static
map is deliberate here rather than a database-driven/API-fetched system:
five roles, seven domains, no per-school customization yet. Revisit if
that ever changes.

Levels are intentionally coarse for now ('full' or absent). A domain not
listed for a role means no access at all — NOT read-only. Read-only-style
access, if ever needed, should be a distinct, deliberately-designed level,
not assumed.
"""

DOMAINS = [
    'students', 'staff', 'attendance', 'fees',
    'communications', 'documents', 'reports',
]

ROLE_PERMISSIONS = {
    'school_admin':   {d: 'full' for d in DOMAINS},
    'branch_manager': {d: 'full' for d in DOMAINS},
    'accountant':     {'fees': 'full'},
    'registrar':      {'students': 'full', 'documents': 'full', 'reports': 'full'},
    # Teachers operate through the separate /teacher/* route tree and its
    # own object-level checks (their own classes only) — not modeled here.
    'teacher':        {},
    # Reserved, no defined feature surface yet. Do not assign in production.
    'receptionist':   {},
}


def has_domain_access(member, domain, level='full'):
    """
    member: a SchoolMember instance (or any object exposing `.role`).
    domain: one of DOMAINS.
    level: the access level required — currently only 'full' is meaningful.
    """
    if member is None:
        return False
    permissions = ROLE_PERMISSIONS.get(member.role, {})
    return permissions.get(domain) == level


def domains_for_role(role):
    """All domains a role has 'full' access to — used to filter the
    dashboard's domain cards to what a user can actually open."""
    return [
        domain for domain, level in ROLE_PERMISSIONS.get(role, {}).items()
        if level == 'full'
    ]