class ExtraFieldValidationError(Exception):
    """Raised when admin-supplied extra_values don't satisfy a template's extra_fields spec."""
    def __init__(self, errors):
        self.errors = errors
        super().__init__(str(errors))


def validate_extra_values(template, extra_values):
    """
    Checks extra_values (dict) against template.extra_fields (list of field specs).
    Raises ExtraFieldValidationError with a dict of {token: message} if anything
    required is missing. Does not mutate extra_values.
    """
    errors = {}
    extra_values = extra_values or {}

    for field in template.extra_fields or []:
        token = field.get("token")
        label = field.get("label", token)
        required = field.get("required", False)

        if required and not extra_values.get(token):
            errors[token] = f"{label} is required."

    if errors:
        raise ExtraFieldValidationError(errors)