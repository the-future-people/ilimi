import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def send_sms(phone_number, message):
    """
    Send an SMS via Arkesel API.
    Phone number should be in international format e.g. 0244941343 → 233244941343
    """
    try:
        formatted_number = format_phone_number(phone_number)

        payload = {
            "action": "send-sms",
            "api_key": settings.ARKESEL_API_KEY,
            "to": formatted_number,
            "from": settings.ARKESEL_SENDER_ID,
            "sms": message,
        }

        response = requests.post(
            "https://sms.arkesel.com/sms/api",
            params=payload,
            timeout=10,
        )

        response_data = response.json()

        if response_data.get("status") == "success":
            logger.info(f"SMS sent to {formatted_number}")
            return True
        else:
            logger.warning(f"SMS failed to {formatted_number}: {response_data}")
            return False

    except Exception as e:
        logger.error(f"SMS error for {phone_number}: {str(e)}")
        return False


def format_phone_number(phone_number):
    """Convert local Ghana number to international format."""
    phone = str(phone_number).strip().replace(" ", "").replace("+", "")
    if phone.startswith("0"):
        phone = "233" + phone[1:]
    elif phone.startswith("233"):
        pass
    else:
        phone = "233" + phone
    return phone