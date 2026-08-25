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
                'message': (
                    data.get('detail') or data.get('message') or 'An error occurred'
                ) if isinstance(data, dict) else 'An error occurred',
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