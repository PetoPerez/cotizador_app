import boto3
from botocore.client import Config
from app.config import settings

_SUPABASE_URL = settings.SUPABASE_URL or ""
_S3_ENDPOINT  = settings.SUPABASE_S3_ENDPOINT or ""
_ACCESS_KEY   = settings.SUPABASE_ACCESS_KEY_ID or ""
_SECRET_KEY   = settings.SUPABASE_SECRET_ACCESS_KEY or ""
_BUCKET       = settings.SUPABASE_BUCKET or ""


def _client():
    return boto3.client(
        "s3",
        endpoint_url=_S3_ENDPOINT,
        aws_access_key_id=_ACCESS_KEY,
        aws_secret_access_key=_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def upload_image(file_bytes: bytes, key: str, content_type: str) -> str:
    _client().put_object(
        Bucket=_BUCKET,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    return f"{_SUPABASE_URL}/storage/v1/object/public/{_BUCKET}/{key}"


def delete_image(key: str) -> None:
    _client().delete_object(Bucket=_BUCKET, Key=key)


def key_from_url(url: str) -> str:
    marker = f"/public/{_BUCKET}/"
    idx = url.find(marker)
    return url[idx + len(marker):] if idx >= 0 else ""
