
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.db import get_db


@pytest.fixture
def client():
    # API tests ke liye database dependency ko mock karo.
    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def registration_payload():
    return {
        "full_name": "Test Customer",
        "email": "test@example.com",
        "phone_number": "9876543210",
        "password": "StrongPass123",
        "profile_photo_url": None,
    }


# Successful registration request
def test_website_register_returns_202(
    client,
    registration_payload,
):
    expected_response = {
        "message": "Verification code sent successfully.",
        "verification_required": True,
    }

    with patch(
        "app.modules.customers.router.WebsiteRegistrationService"
    ) as service_class:
        service_class.return_value.register.return_value = expected_response

        # register() async hai, isliye AsyncMock use karo.
        from unittest.mock import AsyncMock
        service_class.return_value.register = AsyncMock(
            return_value=expected_response
        )

        response = client.post(
            "/api/v1/customers/customers/website/register",
            json=registration_payload,
        )

    assert response.status_code == 202
    assert response.json() == expected_response


# Existing customer registration should return 409
def test_website_register_duplicate_returns_409(
    client,
    registration_payload,
):
    from unittest.mock import AsyncMock

    with patch(
        "app.modules.customers.router.WebsiteRegistrationService"
    ) as service_class:
        service_class.return_value.register = AsyncMock(
            side_effect=ValueError("Email is already registered.")
        )

        response = client.post(
            "/api/v1/customers/customers/website/register",
            json=registration_payload,
        )

    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]


# Email/SMS delivery failure should return 503
def test_website_register_delivery_failure_returns_503(
    client,
    registration_payload,
):
    from unittest.mock import AsyncMock

    with patch(
        "app.modules.customers.router.WebsiteRegistrationService"
    ) as service_class:
        service_class.return_value.register = AsyncMock(
            side_effect=RuntimeError("Verification delivery failed.")
        )

        response = client.post(
            "/api/v1/customers/customers/website/register",
            json=registration_payload,
        )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Registration delivery is temporarily unavailable."
    )


# Invalid registration data should return 422
@pytest.mark.parametrize(
    "field,value",
    [
        ("email", "not-an-email"),
        ("password", "short"),
        ("phone_number", "123"),
        ("full_name", "A"),
    ],
)
def test_website_register_invalid_data_returns_422(
    client,
    registration_payload,
    field,
    value,
):
    registration_payload[field] = value

    response = client.post(
        "/api/v1/customers/customers/website/register",
        json=registration_payload,
    )

    assert response.status_code == 422


# Successful OTP verification should return 201
def test_website_verify_otp_returns_201(client):
    from unittest.mock import MagicMock

    customer = MagicMock()
    customer.id = uuid4()
    customer.full_name = "Test Customer"
    customer.email = "test@example.com"
    customer.phone_number = "9876543210"
    customer.profile_photo_url = None
    customer.is_verified = True

    with patch(
        "app.modules.customers.router.WebsiteRegistrationService"
    ) as service_class:
        service_class.return_value.verify.return_value = customer

        response = client.post(
            "/api/v1/customers/customers/website/verify-otp",
            json={
                "email": "test@example.com",
                "otp": "123456",
            },
        )

    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"
    assert response.json()["is_verified"] is True


# Invalid OTP should return 400
def test_website_verify_invalid_otp_returns_400(client):
    with patch(
        "app.modules.customers.router.WebsiteRegistrationService"
    ) as service_class:
        service_class.return_value.verify.side_effect = ValueError(
            "Invalid or expired verification code."
        )

        response = client.post(
            "/api/v1/customers/customers/website/verify-otp",
            json={
                "email": "test@example.com",
                "otp": "000000",
            },
        )

    assert response.status_code == 400


# Malformed OTP should be rejected by schema validation
def test_website_verify_malformed_otp_returns_422(client):
    response = client.post(
        "/api/v1/customers/customers/website/verify-otp",
        json={
            "email": "test@example.com",
            "otp": "12ab",
        },
    )

    assert response.status_code == 422
