import boto3
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
    """Uploads a file-like object to an S3 and returns its public URL"""
    s3_client.upload_fileobj(file_obj, settings.S3_BUCKET_NAME, object_name)
    return object_name

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
    





