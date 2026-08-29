"""
Role -> domain permissions.

Roles and their bundles now live in the database, per school, because
Ghanaian schools distribute the same work differently: a school with no
accounts office gives fees to its administrator, and an assistant head may
run academics at one school and admissions at another. A static map could
not express that.

Levels, weakest first:
  view     - can see, cannot change
  request  - can propose; someone else approves
  full     - can do

A domain not listed for a role means no access at all.
"""
from apps.tenants.models import RolePermission

DOMAINS = [
    'students', 'staff', 'attendance', 'fees', 'admissions',
    'academics', 'communications', 'documents', 'reports', 'parents',
]

LEVEL_RANK = RolePermission.LEVEL_RANK


def _permissions_for(member):
    """
    {domain: level} for this member, cached on the instance.

    Permission checks happen several times per request, and each one was
    a dictionary lookup before. Caching keeps it to one query.
    """
    if member is None:
        return {}

    cached = getattr(member, '_permission_cache', None)
    if cached is not None:
        return cached

    if not member.role_ref_id:
        member._permission_cache = {}
        return {}

    perms = {
        p.domain: p.level
        for p in RolePermission.objects.filter(role_id=member.role_ref_id)
    }
    member._permission_cache = perms
    return perms


def has_domain_access(member, domain, level='full'):
    """
    True when this member's role reaches at least `level` on `domain`.

    Ranked, so full satisfies a request or view requirement, and view
    satisfies neither of the others.
    """
    if member is None:
        return False

    granted = _permissions_for(member).get(domain)
    if not granted:
        return False

    return LEVEL_RANK.get(granted, 0) >= LEVEL_RANK.get(level, 99)


def domains_for_role(member):
    """
    Domains this member can open at all, at any level. Used to filter the
    dashboard cards to what they can actually reach.

    Takes a member now, not a role string, because the bundle belongs to
    the school's role rather than to a global name.
    """
    return sorted(_permissions_for(member).keys())


def role_slug(member):
    """The stable slug, for code that needs to branch on which role this is."""
    if member is None or not member.role_ref_id:
        return None
    return member.role_ref.slug

def is_admin_tier(member):
    """
    True for roles that run or oversee the school rather than one domain.

    Views used to ask 'is this a school_admin or branch_manager', which
    breaks whenever roles change. Where a view really means 'can they do X',
    use has_domain_access instead — this is only for genuinely school-wide
    authority, like approving another person's message.
    """
    return role_slug(member) in OVERSIGHT_ROLES


# ── Lead-tier actions ──────────────────────────────────────────────────────
# Sensitive actions inside an already-accessible domain, e.g. the Main
# Accountant versus a second accountant. Keyed by role slug.

LEAD_ONLY_ACTIONS = {
    ('accounts', 'void_payment'),
    ('accounts', 'edit_fee_structure'),
    ('accounts', 'close_term_books'),
    ('accounts', 'manage_accountants'),
    ('administrator', 'approve_enrolment'),
    ('administrator', 'generate_official_document'),
    ('administrator', 'manage_registrars'),
}

# Roles that oversee rather than operate. Not subject to lead tiering.
OVERSIGHT_ROLES = {'proprietor', 'assistant_head'}


def can_perform(member, action):
    """
    Gate a sensitive within-domain action.

    Domain access is a separate, earlier check. This only covers the
    smaller set of actions that additionally require lead status.
    """
    if member is None:
        return False

    slug = role_slug(member)
    if slug in OVERSIGHT_ROLES:
        return True
    if (slug, action) not in LEAD_ONLY_ACTIONS:
        return True
    return bool(member.is_lead)


# ── Lesson plan vetting ────────────────────────────────────────────────────
# Academics vets facilitators; the assistant head and proprietor vet
# academics when they teach. Nobody vets their own plan.

VETTING_ROLES = {'academics', 'assistant_head', 'proprietor'}


def can_vet_lesson_plans(member):
    if member is None:
        return False
    return role_slug(member) in VETTING_ROLES


def can_vet_plan(member, plan):
    """A plan's own author can never vet it, whatever their role."""
    if not can_vet_lesson_plans(member):
        return False
    if plan.facilitator_id and plan.facilitator_id == member.id:
        return False
    return True