from rest_framework.views import exception_handler
from apps.core.renderers import IlimiAPIRenderer


def ilimi_exception_handler(exc, context):
    """
    Custom exception handler that formats all errors
    using the Ilimi API response envelope.
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_detail = response.data

        if isinstance(error_detail, dict) and 'detail' in error_detail:
            message = str(error_detail['detail'])
            errors = None
        elif isinstance(error_detail, dict):
            # Pull the real message out rather than saying 'Validation
            # failed' and hiding it in errors. Same extraction the renderer
            # uses, so the two cannot drift apart.
            message = IlimiAPIRenderer._error_message(error_detail)
            errors = error_detail
        else:
            message = str(error_detail)
            errors = None

        response.data = {
            'status': 'error',
            'message': message,
            'data': None,
            'errors': errors,
        }

    return response