
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.config import settings

from app.core.security import hash_password
from app.modules.customers.repository import CustomerRepository
from app.modules.customers.website_registration import (
    clear_otp,
    clear_pending_registration,
    generate_otp,
    get_pending_registration,
    store_otp,
    store_pending_registration,
    verify_stored_otp,
)
from app.modules.customers.sms_service import send_otp_sms
from app.modules.customers.email_service import send_otp_email


class WebsiteRegistrationService:
    def __init__(self, db: Session):
        self.db = db
        self.customer_repo = CustomerRepository(db)

    async def register(
        self,
        full_name: str,
        email: str,
        phone_number: str,
        password: str,
        profile_photo_url: str | None = None,
    ) -> dict:
        normalized_email = email.strip().lower()
        normalized_phone = phone_number.strip()

        if self.customer_repo.get_customer_by_email(normalized_email):
            raise ValueError("Email is already registered.")

        if self.customer_repo.get_customer_by_phone_number(normalized_phone):
            raise ValueError("Phone number is already registered.")

        otp = generate_otp()

        pending_data = {
            "full_name": full_name.strip(),
            "email": normalized_email,
            "phone_number": normalized_phone,
            "password_hash": hash_password(password),
            "profile_photo_url": profile_photo_url,
        }

        # Store pending details and OTP before attempting delivery.
        store_pending_registration(normalized_email, pending_data)
        store_otp(normalized_email, otp)

        try:
            # Attempt both deliveries; do not return the OTP to the caller.
            email_sent = await send_otp_email(normalized_email, otp)

            if settings.environment == "local" and settings.customer_otp_test_mode:
            # Local testing only: SMS is simulated, not delivered.
                sms_sent = True
            else:
                sms_sent = await send_otp_sms(normalized_phone, otp)

            if not email_sent or not sms_sent:
                clear_otp(normalized_email)
                clear_pending_registration(normalized_email)
                raise RuntimeError(
                    "Verification delivery failed. Please try again later."
                )

        except Exception as exc:
            clear_otp(normalized_email)
            clear_pending_registration(normalized_email)
            raise RuntimeError(
                "Verification delivery failed. Please check provider configuration."
            ) from exc

        return {
            "message": "If delivery is available, a verification code has been sent.",
            "verification_required": True,
        }

    def verify(self, email: str, otp: str):
        normalized_email = email.strip().lower()
        pending = get_pending_registration(normalized_email)

        if pending is None:
            raise ValueError("Registration expired. Please register again.")

        if not verify_stored_otp(normalized_email, otp):
            raise ValueError("Invalid or expired verification code.")

        try:
            customer = self.customer_repo.create_website_customer(
                full_name=pending["full_name"],
                phone_number=pending["phone_number"],
                email=pending["email"],
                password_hash=pending["password_hash"],
                profile_photo_url=pending.get("profile_photo_url"),
            )

            customer.is_verified = True
            self.db.commit()
            self.db.refresh(customer)

        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError(
                "Email or phone number is already registered."
            ) from exc

        clear_otp(normalized_email)
        clear_pending_registration(normalized_email)

        return customer
