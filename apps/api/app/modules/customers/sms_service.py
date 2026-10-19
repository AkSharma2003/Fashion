
import httpx

from app.core.config import settings


async def send_otp_sms(phone_number: str, otp: str) -> bool:
    """
    Send the FashionOS-generated OTP through 2Factor.
    The configured template must support the var1 placeholder.
    """
    api_key = settings.twofactor_api_key

    if not api_key:
        raise RuntimeError("TWOFACTOR_API_KEY is not configured")

    url = "https://2factor.in/API/V1/OTP/SEND"

    payload = {
        "to": phone_number,
        "template_name": "FASHIONOS_REGISTER_OTP",
        "var1": otp,
    }

    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            url,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        result = response.json()

    return result.get("status") == "sent"
