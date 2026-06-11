#!/bin/sh
set -e

# Configuration from environment
MINIO_HOST="${MINIO_HOST:-minio:9000}"
MINIO_ACCESS_KEY="${MINIO_ROOT_USER:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_ROOT_PASSWORD:-minioadmin}"
BUCKET_NAME="${AWS_S3_BUCKET:-flexiread-dev}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"

echo "Waiting for MinIO at $MINIO_HOST..."
until mc alias set local http://$MINIO_HOST $MINIO_ACCESS_KEY $MINIO_SECRET_KEY > /dev/null 2>&1; do
  echo "MinIO is not ready yet - waiting..."
  sleep 2
done

# Setup alias
mc alias set local http://$MINIO_HOST $MINIO_ACCESS_KEY $MINIO_SECRET_KEY || true

# Create bucket if it doesn't exist
if ! mc ls local/$BUCKET_NAME > /dev/null 2>&1; then
  echo "Creating bucket: $BUCKET_NAME"
  mc mb local/$BUCKET_NAME || true
else
  echo "Bucket $BUCKET_NAME already exists"
fi

# Set CORS policy
echo "Setting CORS policy..."
cat <<EOF > /tmp/cors.json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
    "AllowedOrigins": ["*"],
    "ExposeHeaders": ["ETag", "x-amz-version-id"],
    "MaxAgeSeconds": 3000
  }
]
EOF
mc cors set local/$BUCKET_NAME /tmp/cors.json || true

# Enable versioning
echo "Enabling versioning..."
mc version enable local/$BUCKET_NAME || true

# Set lifecycle policy
echo "Setting lifecycle policy..."
cat <<EOF > /tmp/lifecycle.json
{
  "Rules": [
    {
      "ID": "delete-old-versions",
      "Status": "Enabled",
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 30
      }
    }
  ]
}
EOF
if [ -f /tmp/lifecycle.json ]; then
    mc ilm import local/$BUCKET_NAME < /tmp/lifecycle.json || true
fi

echo "✓ MinIO initialization complete"
