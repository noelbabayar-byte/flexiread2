"""
S3/MinIO Storage Utility
Handles internal (Docker) and public (Browser) endpoint separation
"""

import os
import logging
from typing import Optional, Tuple
from datetime import timedelta
import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)


class S3Storage:
    """S3/MinIO storage client with internal/public endpoint separation"""
    
    def __init__(self):
        # Internal endpoint (Docker network) - for backend operations
        self.internal_endpoint = os.getenv(
            "AWS_S3_INTERNAL_ENDPOINT_URL",
            "http://minio:9000"
        )
        
        # Public endpoint (Browser access) - for presigned URLs
        self.public_endpoint = os.getenv(
            "AWS_S3_PUBLIC_ENDPOINT_URL",
            "http://localhost:9000"
        )
        
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
        self.bucket = os.getenv("AWS_S3_BUCKET", "flexiread-dev")
        self.region = os.getenv("AWS_S3_REGION", "us-east-1")
        
        # Initialize internal S3 client (for backend operations)
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.internal_endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            config=Config(signature_version="s3v4")
        )
        
        logger.info(f"S3Storage initialized:")
        logger.info(f"  Internal endpoint: {self.internal_endpoint}")
        logger.info(f"  Public endpoint: {self.public_endpoint}")
        logger.info(f"  Bucket: {self.bucket}")
    
    def generate_presigned_upload_url(
        self,
        key: str,
        expiration: int = 3600,
        content_type: str = "application/octet-stream"
    ) -> Tuple[str, dict]:
        """
        Generate presigned URL for uploading file to S3
        
        Uses PUBLIC endpoint so browser can access it directly
        
        Args:
            key: S3 object key (path)
            expiration: URL expiration in seconds
            content_type: MIME type of the file
            
        Returns:
            Tuple of (presigned_url, response_metadata)
        """
        try:
            # Generate presigned URL using internal client
            # but replace internal endpoint with public endpoint
            response = self.s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ContentType": content_type
                },
                ExpiresIn=expiration
            )
            
            # Replace internal endpoint with public endpoint in URL
            public_url = response.replace(
                self.internal_endpoint,
                self.public_endpoint
            )
            
            logger.info(f"Generated presigned upload URL for key: {key}")
            logger.debug(f"  Internal URL: {response}")
            logger.debug(f"  Public URL: {public_url}")
            
            return public_url, {"expires_in": expiration}
            
        except Exception as e:
            logger.error(f"Error generating presigned upload URL: {str(e)}")
            raise
    
    def generate_presigned_download_url(
        self,
        key: str,
        expiration: int = 3600
    ) -> Tuple[str, dict]:
        """
        Generate presigned URL for downloading file from S3
        
        Uses PUBLIC endpoint so browser can access it directly
        
        Args:
            key: S3 object key (path)
            expiration: URL expiration in seconds
            
        Returns:
            Tuple of (presigned_url, response_metadata)
        """
        try:
            # Generate presigned URL using internal client
            response = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key
                },
                ExpiresIn=expiration
            )
            
            # Replace internal endpoint with public endpoint in URL
            public_url = response.replace(
                self.internal_endpoint,
                self.public_endpoint
            )
            
            logger.info(f"Generated presigned download URL for key: {key}")
            logger.debug(f"  Internal URL: {response}")
            logger.debug(f"  Public URL: {public_url}")
            
            return public_url, {"expires_in": expiration}
            
        except Exception as e:
            logger.error(f"Error generating presigned download URL: {str(e)}")
            raise
    
    def upload_file(
        self,
        key: str,
        file_path: str,
        content_type: str = "application/octet-stream"
    ) -> dict:
        """
        Upload file from disk to S3
        
        Uses INTERNAL endpoint (backend operation)
        
        Args:
            key: S3 object key (path)
            file_path: Local file path
            content_type: MIME type
            
        Returns:
            Response metadata
        """
        try:
            with open(file_path, "rb") as f:
                response = self.s3_client.put_object(
                    Bucket=self.bucket,
                    Key=key,
                    Body=f,
                    ContentType=content_type
                )
            
            logger.info(f"Uploaded file to S3: {key}")
            return {
                "key": key,
                "etag": response.get("ETag"),
                "version_id": response.get("VersionId")
            }
            
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise
    
    def upload_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream"
    ) -> dict:
        """
        Upload bytes to S3
        
        Uses INTERNAL endpoint (backend operation)
        
        Args:
            key: S3 object key (path)
            data: Bytes to upload
            content_type: MIME type
            
        Returns:
            Response metadata
        """
        try:
            response = self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type
            )
            
            logger.info(f"Uploaded {len(data)} bytes to S3: {key}")
            return {
                "key": key,
                "size_bytes": len(data),
                "etag": response.get("ETag"),
                "version_id": response.get("VersionId")
            }
            
        except Exception as e:
            logger.error(f"Error uploading bytes: {str(e)}")
            raise
    
    def download_file(
        self,
        key: str,
        file_path: str
    ) -> dict:
        """
        Download file from S3 to disk
        
        Uses INTERNAL endpoint (backend operation)
        
        Args:
            key: S3 object key (path)
            file_path: Local file path to save to
            
        Returns:
            Response metadata
        """
        try:
            self.s3_client.download_file(
                self.bucket,
                key,
                file_path
            )
            
            logger.info(f"Downloaded file from S3: {key}")
            return {"key": key, "file_path": file_path}
            
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            raise
    
    def download_bytes(self, key: str) -> bytes:
        """
        Download file from S3 as bytes
        
        Uses INTERNAL endpoint (backend operation)
        
        Args:
            key: S3 object key (path)
            
        Returns:
            File bytes
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=key
            )
            
            data = response["Body"].read()
            logger.info(f"Downloaded {len(data)} bytes from S3: {key}")
            return data
            
        except Exception as e:
            logger.error(f"Error downloading bytes: {str(e)}")
            raise
    
    def delete_file(self, key: str) -> dict:
        """
        Delete file from S3
        
        Uses INTERNAL endpoint (backend operation)
        
        Args:
            key: S3 object key (path)
            
        Returns:
            Response metadata
        """
        try:
            response = self.s3_client.delete_object(
                Bucket=self.bucket,
                Key=key
            )
            
            logger.info(f"Deleted file from S3: {key}")
            return {
                "key": key,
                "delete_marker": response.get("DeleteMarker"),
                "version_id": response.get("VersionId")
            }
            
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            raise
    
    def file_exists(self, key: str) -> bool:
        """
        Check if file exists in S3
        
        Uses INTERNAL endpoint (backend operation)
        
        Args:
            key: S3 object key (path)
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=key)
            return True
        except self.s3_client.exceptions.NoSuchKey:
            return False
        except Exception as e:
            logger.error(f"Error checking file existence: {str(e)}")
            raise
    
    def list_files(self, prefix: str = "") -> list:
        """
        List files in S3 bucket
        
        Uses INTERNAL endpoint (backend operation)
        
        Args:
            prefix: Filter by prefix
            
        Returns:
            List of file keys
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )
            
            files = [obj["Key"] for obj in response.get("Contents", [])]
            logger.info(f"Listed {len(files)} files with prefix: {prefix}")
            return files
            
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            raise


# Singleton instance
_s3_storage: Optional[S3Storage] = None


def get_s3_storage() -> S3Storage:
    """Get or create S3 storage singleton"""
    global _s3_storage
    if _s3_storage is None:
        _s3_storage = S3Storage()
    return _s3_storage
