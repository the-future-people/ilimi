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

# Sensitive, within-domain actions that require lead status on top of
# ordinary domain access. Keyed by (role, action) so each role's lead
# powers are named explicitly rather than inferred.
LEAD_ONLY_ACTIONS = {
    ('accountant', 'void_payment'),
    ('accountant', 'edit_fee_structure'),
    ('accountant', 'close_term_books'),
    ('accountant', 'manage_accountants'),
    ('registrar', 'approve_enrolment'),
    ('registrar', 'generate_official_document'),
    ('registrar', 'manage_registrars'),
}


def can_perform(member, action):
    """
    Check a specific sensitive action, e.g. can_perform(member, 'void_payment').

    Domain access (can they open Fees at all) is a separate, earlier check
    via has_domain_access — this only gates the smaller set of actions that
    additionally require lead status within an already-accessible domain.
    Admin-tier roles bypass this entirely; they're not subject to lead
    tiering since they already have full access to everything.
    """
    if member is None:
        return False
    if member.role in ('school_admin', 'branch_manager'):
        return True
    if (member.role, action) not in LEAD_ONLY_ACTIONS:
        # Not a lead-gated action at all — ordinary domain access already
        # covers it, nothing further to check here.
        return True
    return bool(member.is_lead)