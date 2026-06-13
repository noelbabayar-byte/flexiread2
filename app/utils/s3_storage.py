"""
AWS S3 storage utilities for PDF upload and processed content management.
Handles file operations with proper error handling and logging.
"""

import boto3
import logging
import json
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError
from app.core.config import settings

logger = logging.getLogger(__name__)


class S3Storage:
    """S3 storage client for PDF and content management."""

    _client = None  # Internal client (Docker network) - upload/download
    _public_client = None  # Public client (browser-reachable) - presigned URLs

    def __init__(self):
        """Initialize S3 clients with AWS credentials, ensuring singleton pattern."""
        if S3Storage._client is None:
            S3Storage._client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION,
                endpoint_url=settings.AWS_S3_INTERNAL_ENDPOINT_URL,  # For MinIO
            )
            logger.info("S3 internal client initialized.")

        # Presigned URLs must point to an endpoint the browser can reach, not the
        # Docker-internal hostname. Sign them with the public endpoint.
        if S3Storage._public_client is None:
            public_endpoint = (
                settings.AWS_S3_PUBLIC_ENDPOINT_URL
                or settings.AWS_S3_INTERNAL_ENDPOINT_URL
            )
            S3Storage._public_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION,
                endpoint_url=public_endpoint,
            )
            logger.info("S3 public client initialized: %s", public_endpoint)

        self.client = S3Storage._client
        self.public_client = S3Storage._public_client
        self.bucket = settings.AWS_S3_BUCKET

    def upload_file(
        self, file_path: str, s3_key: str, content_type: str = "application/pdf"
    ) -> Optional[str]:
        """
        Upload file to S3.

        Args:
            file_path: Local file path
            s3_key: S3 object key (path)
            content_type: MIME type

        Returns:
            S3 URL if successful, None otherwise
        """
        try:
            self.client.upload_file(
                file_path, self.bucket, s3_key, ExtraArgs={"ContentType": content_type}
            )
            url = f"s3://{self.bucket}/{s3_key}"
            logger.info(f"File uploaded to S3: {url}")
            return url
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            return None

    def download_file(self, s3_key: str, local_path: str) -> bool:
        """
        Download file from S3.

        Args:
            s3_key: S3 object key
            local_path: Local file path to save

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.download_file(self.bucket, s3_key, local_path)
            logger.info(f"File downloaded from S3: {s3_key} -> {local_path}")
            return True
        except ClientError as e:
            logger.error(f"S3 download failed: {e}")
            return False

    def upload_json(self, data: Dict[str, Any], s3_key: str) -> Optional[str]:
        """
        Upload JSON data to S3.

        Args:
            data: Dictionary to serialize as JSON
            s3_key: S3 object key

        Returns:
            S3 URL if successful, None otherwise
        """
        try:
            json_content = json.dumps(data, ensure_ascii=False, indent=2)
            self.client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=json_content.encode("utf-8"),
                ContentType="application/json",
            )
            url = f"s3://{self.bucket}/{s3_key}"
            logger.info(f"JSON uploaded to S3: {url}")
            return url
        except ClientError as e:
            logger.error(f"S3 JSON upload failed: {e}")
            return None

    def delete_file(self, s3_key: str) -> bool:
        """
        Delete file from S3.

        Args:
            s3_key: S3 object key

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.info(f"File deleted from S3: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"S3 delete failed: {e}")
            return False

    def generate_presigned_url(
        self, s3_key: str, expiration: int = 3600
    ) -> Optional[str]:
        """
        Generate presigned URL for file access.

        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds

        Returns:
            Presigned URL if successful, None otherwise
        """
        try:
            # Sign with the public client so the URL host is browser-reachable.
            url = self.public_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": s3_key,
                    "ContentType": "application/pdf",
                },
                ExpiresIn=expiration,
            )
            return url
        except ClientError as e:
            logger.error(f"Presigned URL generation failed: {e}")
            return None

    def download_json(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """
        Download and parse a JSON object from S3.

        Args:
            s3_key: S3 object key

        Returns:
            Parsed dict if successful, None otherwise
        """
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=s3_key)
            body = response["Body"].read().decode("utf-8")
            return json.loads(body)
        except ClientError as e:
            logger.error(f"S3 JSON download failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"S3 JSON parse failed for {s3_key}: {e}")
            return None


# Global S3 storage instance
s3_storage = S3Storage()
