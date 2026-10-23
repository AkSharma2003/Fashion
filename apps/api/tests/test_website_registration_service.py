import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.customers.website_registration_service import (
    WebsiteRegistrationService,
)


# Common database mock
@pytest.fixture
def db():
    return MagicMock()


# Service fixture with mocked repository
@pytest.fixture
def service(db):
    instance = WebsiteRegistrationService(db)
    instance.customer_repo = MagicMock()
    return instance


# Reusable registration test data
@pytest.fixture
def registration_data():
    return {
        "full_name": "Test Customer",
        "email": "test@example.com",
        "phone_number": "9876543210",
        "password": "StrongPass123",
    }


# Reject an already registered email
def test_register_rejects_existing_email(service, registration_data):
    service.customer_repo.get_customer_by_email.return_value = object()

    with pytest.raises(ValueError, match="Email is already registered"):
        asyncio.run(service.register(**registration_data))


# Reject an already registered phone number
def test_register_rejects_existing_phone(service, registration_data):
    service.customer_repo.get_customer_by_email.return_value = None
    service.customer_repo.get_customer_by_phone_number.return_value = object()

    with pytest.raises(ValueError, match="Phone number is already registered"):
        asyncio.run(service.register(**registration_data))


# Send OTP without returning it to the client
def test_register_sends_otp_and_does_not_return_it(
    service,
    registration_data,
):
    service.customer_repo.get_customer_by_email.return_value = None
    service.customer_repo.get_customer_by_phone_number.return_value = None

    with (
        patch(
            "app.modules.customers.website_registration_service.generate_otp",
            return_value="123456",
        ),
        patch(
            "app.modules.customers.website_registration_service.store_pending_registration"
        ) as store_pending,
        patch(
            "app.modules.customers.website_registration_service.store_otp"
        ) as store_otp,
        patch(
            "app.modules.customers.website_registration_service.send_otp_email",
            new_callable=AsyncMock,
            return_value=True,
        ) as send_email,
        patch(
            "app.modules.customers.website_registration_service.send_otp_sms",
            new_callable=AsyncMock,
            return_value=True,
        ) as send_sms,
        patch(
            "app.modules.customers.website_registration_service.settings"
        ) as settings,
    ):
        settings.environment = "production"

        result = asyncio.run(
            service.register(**registration_data)
        )

    assert result["verification_required"] is True
    assert "123456" not in str(result)

    store_pending.assert_called_once()
    store_otp.assert_called_once_with(
        registration_data["email"],
        "123456",
    )
    send_email.assert_awaited_once_with(
        registration_data["email"],
        "123456",
    )
    send_sms.assert_awaited_once_with(
        registration_data["phone_number"],
        "123456",
    )


# Clear pending data when OTP delivery fails
def test_register_clears_pending_data_when_email_delivery_fails(
    service,
    registration_data,
):
    service.customer_repo.get_customer_by_email.return_value = None
    service.customer_repo.get_customer_by_phone_number.return_value = None

    with (
        patch(
            "app.modules.customers.website_registration_service.generate_otp",
            return_value="123456",
        ),
        patch(
            "app.modules.customers.website_registration_service.store_pending_registration"
        ),
        patch(
            "app.modules.customers.website_registration_service.store_otp"
        ),
        patch(
            "app.modules.customers.website_registration_service.send_otp_email",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            "app.modules.customers.website_registration_service.send_otp_sms",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.modules.customers.website_registration_service.clear_otp"
        ) as clear_otp,
        patch(
            "app.modules.customers.website_registration_service.clear_pending_registration"
        ) as clear_pending,
        patch(
            "app.modules.customers.website_registration_service.settings"
        ) as settings,
    ):
        settings.environment = "production"

        with pytest.raises(
            RuntimeError,
            match="Verification delivery failed",
        ):
            asyncio.run(
                service.register(**registration_data)
            )

    clear_otp.assert_called_with(registration_data["email"])
    clear_pending.assert_called_with(registration_data["email"])


# Reject verification when registration has expired
def test_verify_rejects_missing_pending_registration(
    service,
    registration_data,
):
    with patch(
        "app.modules.customers.website_registration_service.get_pending_registration",
        return_value=None,
    ):
        with pytest.raises(ValueError, match="Registration expired"):
            service.verify(
                registration_data["email"],
                "123456",
            )


# Reject an invalid OTP
def test_verify_rejects_invalid_otp(service, registration_data):
    with (
        patch(
            "app.modules.customers.website_registration_service.get_pending_registration",
            return_value={"email": registration_data["email"]},
        ),
        patch(
            "app.modules.customers.website_registration_service.verify_stored_otp",
            return_value=False,
        ),
    ):
        with pytest.raises(ValueError, match="Invalid or expired"):
            service.verify(
                registration_data["email"],
                "000000",
            )


# Create and verify the customer after successful OTP verification
def test_verify_creates_verified_customer(
    service,
    registration_data,
):
    pending = {
        "full_name": registration_data["full_name"],
        "email": registration_data["email"],
        "phone_number": registration_data["phone_number"],
        "password_hash": "hashed-password",
        "profile_photo_url": None,
    }

    customer = MagicMock()
    customer.is_verified = False

    # verify() calls this repository method synchronously.
    service.customer_repo.create_website_customer = MagicMock(
        return_value=customer
    )

    with (
        patch(
            "app.modules.customers.website_registration_service.get_pending_registration",
            return_value=pending,
        ),
        patch(
            "app.modules.customers.website_registration_service.verify_stored_otp",
            return_value=True,
        ),
        patch(
            "app.modules.customers.website_registration_service.clear_otp"
        ) as clear_otp,
        patch(
            "app.modules.customers.website_registration_service.clear_pending_registration"
        ) as clear_pending,
    ):
        result = service.verify(
            registration_data["email"].upper(),
            "123456",
        )

    assert result is customer
    assert customer.is_verified is True

    service.customer_repo.create_website_customer.assert_called_once()
    service.db.commit.assert_called_once()
    service.db.refresh.assert_called_once_with(customer)

    clear_otp.assert_called_once_with(registration_data["email"])
    clear_pending.assert_called_once_with(registration_data["email"])