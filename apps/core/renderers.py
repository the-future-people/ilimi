import json
from rest_framework.renderers import JSONRenderer


class IlimiAPIRenderer(JSONRenderer):
    """
    Custom renderer that enforces a consistent API response format:
    {
        "status": "success" | "error",
        "message": "...",
        "data": {...} | null,
        "errors": {...} | null
    }
    """
    charset = 'utf-8'

    @staticmethod
    def _error_message(data):
        """
        Pull out something a person can read.

        DRF puts errors raised by a serializer's validate() under
        non_field_errors, and field errors under the field name. Reading
        only 'detail' and 'message' left both rendering as a generic
        'An error occurred'.
        """
        if not isinstance(data, dict):
            return 'An error occurred'

        for key in ('detail', 'message'):
            value = data.get(key)
            if isinstance(value, str) and value:
                return value

        non_field = data.get('non_field_errors')
        if isinstance(non_field, (list, tuple)) and non_field:
            return str(non_field[0])

        # Fall back to the first field error, named so the person knows
        # which field to fix.
        for field, value in data.items():
            if isinstance(value, (list, tuple)) and value:
                first = str(value[0])
                return first if field == 'non_field_errors' else f'{field}: {first}'
            if isinstance(value, str) and value:
                return value

        return 'An error occurred'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response') if renderer_context else None
        status_code = response.status_code if response else 200

        is_error = status_code >= 400

        if isinstance(data, dict) and 'status' in data and 'data' in data:
            # Already formatted — pass through
            envelope = data
        elif is_error:
            envelope = {
                'status': 'error',
                'message': self._error_message(data),
                'data': None,
                'errors': data if isinstance(data, dict) else None,
            }
        else:
            envelope = {
                'status': 'success',
                'message': data.pop('message', 'Request successful') if isinstance(data, dict) else 'Request successful',
                'data': data,
                'errors': None,
            }

        return json.dumps(
            envelope, ensure_ascii=False, indent=None, default=str
        ).encode(self.charset)