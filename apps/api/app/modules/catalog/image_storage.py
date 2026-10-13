
import uuid
from io import BytesIO
from pathlib import Path

import boto3
from PIL import Image, UnidentifiedImageError

from app.core.config import settings


# Allowed product image formats and their extensions
ALLOWED_CONTENT_TYPES = {
    "image/jpeg": (".jpg", "JPEG"),
    "image/png": (".png", "PNG"),
    "image/webp": (".webp", "WEBP"),
}


def get_r2_client():
    """Create an S3-compatible client for Cloudflare R2."""
    return boto3.client(
        "s3",
        endpoint_url=settings.image_storage_endpoint,
        aws_access_key_id=settings.image_storage_access_key,
        aws_secret_access_key=settings.image_storage_secret_key,
        region_name=settings.image_storage_region,
    )


def validate_image(file_content: bytes, content_type: str) -> None:
    """Validate the actual image format, not just the declared MIME type."""

    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(
            "Unsupported image type. Use JPEG, PNG, or WebP."
        )

    if not file_content:
        raise ValueError("The image file is empty.")

    max_size = settings.image_storage_max_file_size_mb * 1024 * 1024
    if len(file_content) > max_size:
        raise ValueError(
            f"Image exceeds the {settings.image_storage_max_file_size_mb} MB limit."
        )

    expected_format = ALLOWED_CONTENT_TYPES[content_type][1]

    try:
        # Check the file's actual image format.
        with Image.open(BytesIO(file_content)) as image:
            if image.format != expected_format:
                raise ValueError(
                    "The file content does not match the declared image type."
                )

            # Verify the image data is not corrupted.
            image.verify()

        # Reopen and decode the image to catch invalid image data.
        with Image.open(BytesIO(file_content)) as image:
            image.load()

    except UnidentifiedImageError as exc:
        raise ValueError("The uploaded file is not a valid image.") from exc
    except OSError as exc:
        raise ValueError("The uploaded image is invalid or corrupted.") from exc


def upload_product_image(
    file_content: bytes,
    content_type: str,
    original_filename: str,
) -> dict:
    """Validate and upload a product image to R2."""

    validate_image(file_content, content_type)

    extension = ALLOWED_CONTENT_TYPES[content_type][0]
    image_id = uuid.uuid4().hex
    object_key = f"products/{image_id}{extension}"

    client = get_r2_client()
    client.put_object(
        Bucket=settings.image_storage_bucket,
        Key=object_key,
        Body=file_content,
        ContentType=content_type,
    )

    return {
        "object_key": object_key,
        "original_filename": Path(original_filename).name,
        "content_type": content_type,
        "size_bytes": len(file_content),
    }


def delete_product_image(object_key: str) -> None:
    """Delete a product image from R2."""
    if not object_key.startswith("products/"):
        raise ValueError("Invalid product image key.")

    client = get_r2_client()
    client.delete_object(
        Bucket=settings.image_storage_bucket,
        Key=object_key,
    )


def get_product_image_url(object_key: str) -> str | None:
    """Return the public URL for a product image."""
    base_url = settings.image_storage_public_base_url

    if not base_url:
        return None

    return f"{base_url.rstrip('/')}/{object_key.lstrip('/')}"