"""
Usernames — the name a person signs in with.

Chosen by the user at setup, unique across all of Ilimi, and deliberately
not tied to a school so it survives someone moving or working at two.
"""
import re

from apps.accounts.models import User

MIN_LENGTH = 3
MAX_LENGTH = 30

# Must start with a letter, then letters, digits, dots or underscores.
PATTERN = re.compile(r'^[a-z][a-z0-9._]{2,29}$')

# Names that would let someone pose as the platform or the school office.
RESERVED = {
    'admin', 'administrator', 'root', 'system', 'support', 'help',
    'ilimi', 'ilimischools', 'ilimighana', 'school', 'office', 'staff',
    'teacher', 'parent', 'student', 'headmaster', 'head', 'bursar',
    'accounts', 'billing', 'security', 'noreply', 'no-reply', 'test',
}


class InvalidUsername(ValueError):
    """Raised when a username cannot be used."""


def normalise_username(raw):
    """Lowercase and trim. Does not validate."""
    if not raw:
        return ''
    return str(raw).strip().lower()


def validate_username(raw):
    """
    Return the normalised username, or raise InvalidUsername with a
    message written for the person typing it.
    """
    name = normalise_username(raw)

    if not name:
        raise InvalidUsername('Choose a username.')
    if len(name) < MIN_LENGTH:
        raise InvalidUsername(f'Use at least {MIN_LENGTH} characters.')
    if len(name) > MAX_LENGTH:
        raise InvalidUsername(f'Use no more than {MAX_LENGTH} characters.')
    if not PATTERN.match(name):
        raise InvalidUsername(
            'Start with a letter and use only letters, numbers, dots '
            'or underscores.'
        )
    if name in RESERVED:
        raise InvalidUsername('That username is not available.')

    return name


def is_available(raw, exclude_user_id=None):
    """
    True when the username is valid and unclaimed. Invalid names report
    unavailable rather than raising, so the live checker on the setup
    page has one thing to render.
    """
    try:
        name = validate_username(raw)
    except InvalidUsername:
        return False

    qs = User.objects.filter(username=name)
    if exclude_user_id:
        qs = qs.exclude(pk=exclude_user_id)
    return not qs.exists()


def suggest_usernames(first_name, last_name, limit=3):
    """
    Offer a few starting points. These are suggestions only — the person
    decides. Ghanaian names do not map reliably onto first and last
    fields, so no generated value is ever applied without confirmation.
    """
    words = [
        re.sub(r'[^a-z]', '', w)
        for w in normalise_username(first_name).split()
    ]
    words = [w for w in words if w]

    first = ''.join(words)
    last = re.sub(r'[^a-z]', '', normalise_username(last_name))

    candidates = []
    if first:
        candidates.append(first)
    # A first-name field often holds a title or an honorific alongside the
    # name people actually use, so each word is offered separately.
    if len(words) > 1:
        candidates.extend(words)
    if first and last:
        candidates.append(f'{first}.{last}')
        candidates.append(f'{first}{last[0]}')
    if last:
        candidates.append(last)

    out = []
    for c in candidates:
        if len(out) >= limit:
            break
        if len(c) < MIN_LENGTH or c in out:
            continue
        if is_available(c):
            out.append(c)

    # Fall back to numbered variants when everything obvious is taken.
    base = first or last or 'user'
    n = 1
    while len(out) < limit and n < 100:
        candidate = f'{base}{n}'
        if is_available(candidate) and candidate not in out:
            out.append(candidate)
        n += 1

    return out