import requests
import logging
from django.conf import settings

from apps.core.phone import normalise_phone

logger = logging.getLogger(__name__)


class MNotifySMSBackend:
    """
    Production SMS backend using the mNotify BMS API v2.
    https://readthedocs.mnotify.com

    The API key travels as a query parameter, so it must never be
    written to logs.
    """

    API_URL = 'https://api.mnotify.com/api/sms/quick'

    def send(self, recipient, message, sender_id=None):
        api_key = getattr(settings, 'SMS_API_KEY', '')
        sender = sender_id or settings.SMS_SENDER_ID

        if not api_key:
            logger.error('SMS not sent: SMS_API_KEY is not configured.')
            return {'status': 'error', 'message': 'SMS is not configured.'}

        phone = self._to_local(normalise_phone(recipient))

        payload = {
            'recipient': [phone],
            'sender': sender,
            'message': message,
            'is_schedule': False,
            'schedule_date': '',
        }

        try:
            response = requests.post(
                self.API_URL,
                params={'key': api_key},
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            # mNotify answers 200 even when it rejects the message, so the
            # body decides, not the HTTP status.
            if data.get('status') != 'success':
                logger.error(f"SMS rejected for {phone}: {data}")
                return {
                    'status': 'error',
                    'message': data.get('message', 'SMS gateway rejected the message.'),
                    'data': data,
                }

            logger.info(f"SMS sent to {phone}: {data.get('code')}")
            return {'status': 'success', 'data': data}

        except requests.exceptions.Timeout:
            logger.error(f"SMS timeout sending to {phone}")
            return {'status': 'error', 'message': 'SMS gateway timeout'}

        except requests.exceptions.RequestException as e:
            logger.error(f"SMS error sending to {phone}: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def _to_local(self, phone):
        """
        mNotify's examples use the local 0XXXXXXXXX form, so E.164 is
        converted back at the boundary. Storage stays canonical.
        """
        if phone.startswith('+233'):
            return '0' + phone[4:]
        return phone