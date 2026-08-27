"""
Canonical phone handling for Ghanaian numbers.

Single source of truth. SMS backends, login lookups and any future
verification flow all normalise through here so that 0572140432,
+233 57 214 0432 and 233-57-214-0432 resolve to one stored value.
"""
import re

COUNTRY_CODE = '233'
NATIONAL_LENGTH = 9  # digits after the country code


class InvalidPhoneNumber(ValueError):
    """Raised when a value cannot be read as a Ghanaian phone number."""


def normalise_phone(raw, strict=False):
    """
    Return a number in E.164 form, e.g. '+233572140432'.

    Returns '' for empty input. With strict=True, raises
    InvalidPhoneNumber instead of returning a value that is not a
    plausible Ghanaian number.
    """
    if not raw:
        return ''

    digits = re.sub(r'\D', '', str(raw))

    if digits.startswith('00' + COUNTRY_CODE):
        digits = digits[2:]
    if digits.startswith(COUNTRY_CODE):
        national = digits[len(COUNTRY_CODE):]
    elif digits.startswith('0'):
        national = digits[1:]
    else:
        national = digits

    if len(national) != NATIONAL_LENGTH:
        if strict:
            raise InvalidPhoneNumber(
                f"'{raw}' is not a valid Ghanaian phone number."
            )
        return str(raw).strip()

    return f'+{COUNTRY_CODE}{national}'


def is_valid_phone(raw):
    if not raw:
        return False
    try:
        normalise_phone(raw, strict=True)
        return True
    except InvalidPhoneNumber:
        return False