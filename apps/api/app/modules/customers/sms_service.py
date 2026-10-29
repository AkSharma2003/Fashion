
import httpx

from app.core.config import settings

import httpx

from app.core.config import settings


async def send_otp_sms(phone_number: str, otp: str) -> bool:
    api_key = settings.twofactor_api_key

    if not api_key:
        raise RuntimeError("TWOFACTOR_API_KEY is not configured")

    phone_number = phone_number.strip().replace(" ", "")

    if phone_number.startswith("+91"):
        phone_number = phone_number[3:]
    elif phone_number.startswith("91") and len(phone_number) == 12:
        phone_number = phone_number[2:]

    if len(phone_number) != 10 or not phone_number.isdigit():
        raise ValueError("Invalid Indian mobile number format")

    template_name = "FASHIONOS_REGISTER_OTP"

    url = (
        f"https://2factor.in/API/V1/{api_key}/SMS/"
        f"{phone_number}/{otp}/{template_name}"
    )

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url)

    print("2Factor HTTP status:", response.status_code)
    print("2Factor response:", response.text[:300])

    response.raise_for_status()

    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError("Invalid response from SMS provider") from exc

    return str(result.get("Status", "")).lower() == "success"