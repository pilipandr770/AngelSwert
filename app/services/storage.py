from urllib.parse import quote

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from flask import current_app


def _s3_client():
    region = current_app.config.get("S3_REGION") or None
    endpoint_url = current_app.config.get("S3_ENDPOINT_URL") or None
    return boto3.client("s3", region_name=region, endpoint_url=endpoint_url)


def s3_enabled() -> bool:
    return bool(current_app.config.get("S3_UPLOADS_ENABLED") and current_app.config.get("S3_BUCKET"))


def _public_url_for_key(bucket: str, key: str) -> str:
    base = (current_app.config.get("S3_PUBLIC_BASE_URL") or "").strip()
    encoded_key = quote(key, safe="/")
    if base:
        return f"{base.rstrip('/')}/{encoded_key}"

    endpoint_url = (current_app.config.get("S3_ENDPOINT_URL") or "").strip()
    region = (current_app.config.get("S3_REGION") or "").strip()

    if endpoint_url and "amazonaws.com" not in endpoint_url:
        return f"{endpoint_url.rstrip('/')}/{bucket}/{encoded_key}"

    if region and region != "us-east-1":
        return f"https://{bucket}.s3.{region}.amazonaws.com/{encoded_key}"
    return f"https://{bucket}.s3.amazonaws.com/{encoded_key}"


def upload_bytes_to_s3(data: bytes, relative_key: str, content_type: str | None = None) -> str:
    bucket = (current_app.config.get("S3_BUCKET") or "").strip()
    if not bucket:
        raise RuntimeError("S3_BUCKET is not configured")

    key_prefix = (current_app.config.get("S3_KEY_PREFIX") or "").strip().strip("/")
    key = f"{key_prefix}/{relative_key.lstrip('/')}" if key_prefix else relative_key.lstrip("/")

    payload = {
        "Bucket": bucket,
        "Key": key,
        "Body": data,
        "CacheControl": "public, max-age=31536000, immutable",
    }
    if content_type:
        payload["ContentType"] = content_type

    client = _s3_client()
    try:
        client.put_object(**payload)
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError(f"S3 upload failed for key '{key}': {exc}") from exc

    return _public_url_for_key(bucket=bucket, key=key)
