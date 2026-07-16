from django.template import engines

from .context import build_standard_context
from .validators import validate_extra_values

django_engine = engines["django"]


def build_full_context(student, template, extra_values=None):
    """
    Merges standard tokens (student/school/guardian/date) with
    admin-supplied extra_values for this template. Validates
    extra_values against template.extra_fields first.
    """
    validate_extra_values(template, extra_values)

    context = build_standard_context(student)
    context.update(extra_values or {})
    return context


def render_document_html(student, template, extra_values=None):
    """
    Renders the final HTML for a document, given a student and a
    DocumentTemplate. Handles both templated docs (body_html has
    tokens filled directly) and computed docs (body_html is a wrapper,
    {{computed_content}} is filled by a dedicated data-assembly function).

    Raises ExtraFieldValidationError if required extra_values are missing.
    """
    context = build_full_context(student, template, extra_values)

    if template.is_computed:
        context["computed_content"] = _build_computed_content(student, template, context)

    django_template = django_engine.from_string(template.body_html)
    return django_template.render(context)


def _build_computed_content(student, template, context):
    """
    Extension point for computed documents (e.g. Transcript). Not yet
    implemented — build order per continuity doc has Transcript after
    Recommendation Letter and Introduction Letter.
    """
    if template.document_type == "transcript":
        raise NotImplementedError("Transcript computed-content assembly not yet built.")
    raise NotImplementedError(
        f"No computed-content handler for document_type='{template.document_type}'."
    )