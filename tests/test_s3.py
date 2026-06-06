from pathlib import Path

import boto3
from moto import mock_aws

from app.core.config import settings
from app.utils.s3_storage import S3Storage


@mock_aws
def test_s3_upload_and_delete_file(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "app.utils.s3_storage.settings.AWS_S3_INTERNAL_ENDPOINT_URL", None
    )
    monkeypatch.setattr("app.utils.s3_storage.S3Storage._client", None)

    s3 = boto3.client("s3", region_name=settings.AWS_S3_REGION)
    s3.create_bucket(Bucket=settings.AWS_S3_BUCKET)

    storage = S3Storage()
    local_file = tmp_path / "sample.pdf"
    local_file.write_bytes(b"%PDF-1.4 test")

    uploaded_url = storage.upload_file(str(local_file), "uploads/sample.pdf")

    assert uploaded_url == f"s3://{settings.AWS_S3_BUCKET}/uploads/sample.pdf"
    assert storage.delete_file("uploads/sample.pdf") is True


@mock_aws
def test_s3_upload_json(monkeypatch):
    monkeypatch.setattr(
        "app.utils.s3_storage.settings.AWS_S3_INTERNAL_ENDPOINT_URL", None
    )
    monkeypatch.setattr("app.utils.s3_storage.S3Storage._client", None)

    s3 = boto3.client("s3", region_name=settings.AWS_S3_REGION)
    s3.create_bucket(Bucket=settings.AWS_S3_BUCKET)

    storage = S3Storage()
    uploaded_url = storage.upload_json({"pages": []}, "processed/content.json")

    assert uploaded_url == f"s3://{settings.AWS_S3_BUCKET}/processed/content.json"
