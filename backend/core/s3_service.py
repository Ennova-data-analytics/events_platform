import boto3
import mimetypes
import io
from botocore.client import Config
from core.config import settings

s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        endpoint_url=settings.S3_ENDPOINT_URL,
        region_name="auto",
        config=Config(
            connect_timeout=10,                 
            read_timeout=60,
            retries={"max_attempts": 3}
        ))

def upload_file_to_s3(file_obj, object_name: str) -> str:
    """Uploads a file-like object to R2 and returns its public URL"""
    content_type, _ = mimetypes.guess_type(object_name)
    if not content_type:
        content_type = 'application/octet-stream'

    extra_args = {
        'CacheControl': 'public, max-age=31536000', 
        'ContentType': content_type
    }

    s3_client.upload_fileobj(
        file_obj,
        settings.S3_BUCKET_NAME,
        object_name,
        ExtraArgs=extra_args
    )

    public_url = f"{settings.R2_PUBLIC_DOMAIN}/{object_name}"
    return public_url

def upload_file_to_s3_from_bytes(file_bytes: io.BytesIO, object_name: str, content_type: str = 'application/octet-stream') -> str:
    """
    Upload a file to S3 from bytes buffer
    """
    file_bytes.seek(0)

    extra_args = {
        'CacheControl': 'public, max-age=31536000',
        'ContentType': content_type
    }

    s3_client.upload_fileobj(
        file_bytes,
        settings.S3_BUCKET_NAME,
        object_name,
        ExtraArgs=extra_args
    )

    public_url = f"{settings.R2_PUBLIC_DOMAIN}/{object_name}"
    return public_url

def get_object_bytes(object_name: str) -> bytes | None:
    """Download an S3 object's bytes (used for server-side CV parsing)."""
    try:
        response = s3_client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=object_name)
        return response["Body"].read()
    except Exception as e:
        print(f"Error downloading object {object_name}: {e}")
        return None


def delete_object(object_name: str) -> bool:
    """Delete an S3 object (used by the GDPR retention job)."""
    try:
        s3_client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=object_name)
        return True
    except Exception as e:
        print(f"Error deleting object {object_name}: {e}")
        return False


def generate_predesigned_url(object_name: str) -> str:
    """Generates a predesigned URL to share a private S3 object"""
    try:
        response = s3_client.generate_presigned_url(
            'get_object',
            Params = {'Bucket': settings.S3_BUCKET_NAME, 'Key': object_name},
            ExpiresIn=3600
        )
        return response
    except Exception as e:
        print(f"Error generating URL: {e}")
    





