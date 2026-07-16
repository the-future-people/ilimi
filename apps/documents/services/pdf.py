from io import BytesIO

from weasyprint import HTML


def render_pdf(html_string, base_url=None):
    """
    Converts final merged HTML into PDF bytes. base_url lets relative
    asset paths (e.g. school logo via MEDIA_URL) resolve correctly —
    pass request.build_absolute_uri('/') or settings-derived base when
    calling from a view.
    """
    buffer = BytesIO()
    HTML(string=html_string, base_url=base_url).write_pdf(buffer)
    return buffer.getvalue()