import boto3
from botocore.exceptions import ClientError
from app.core.config import settings

from loguru import logger

class StorageService:
    def __init__(self):
        # We only initialize if the user provides an endpoint.
        # This prevents crashes when the env isn't populated purely for dev.
        self.bucket = settings.r2_bucket_name

        if settings.r2_endpoint_url and settings.r2_access_key_id:
            self.s3 = boto3.client(
                "s3",
                endpoint_url=settings.r2_endpoint_url,
                aws_access_key_id=settings.r2_access_key_id,
                aws_secret_access_key=settings.r2_secret_access_key,
                region_name="auto", # R2 uses auto region
            )
        else:
            self.s3 = None

    def upload_file(self, file_bytes: bytes, object_key: str, content_type: str) -> bool:
        """
        Uploads a file to Cloudflare R2.
        """
        if not self.s3:
            # If no S3 client, just pretend it worked (useful for testing without keys)
            return True

        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=file_bytes,
                ContentType=content_type,
            )
            return True
        except ClientError as e:
            logger.error(f"Error uploading to R2: {e}")
            raise Exception(f"Failed to upload file to Cloudflare R2: {str(e)}")

    def generate_presigned_url(self, object_key: str, expiration=3600) -> str:
        """
        Generate a presigned URL to share an S3 object securely.
        """
        if not self.s3:
            # Dummy URL for local fallback
            return f"https://dummy-r2-url/{object_key}"

        try:
            response = self.s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': object_key
                },
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            logger.error(f"Error generating presigned url: {e}")
            return ""

    def delete_file(self, object_key: str) -> bool:
        """
        Delete a file from Cloudflare R2.
        """
        if not self.s3:
            return True

        try:
            self.s3.delete_object(Bucket=self.bucket, Key=object_key)
            return True
        except ClientError as e:
            logger.error(f"Error deleting from R2: {e}")
            return False

storage = StorageService()
