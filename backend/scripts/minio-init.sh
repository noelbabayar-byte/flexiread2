#!/bin/bash

# MinIO Initialization Script
# Creates buckets and configures CORS policies

set -e

# Configuration
MINIO_HOST="${MINIO_HOST:-minio:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"
BUCKET_NAME="${BUCKET_NAME:-flexiread-dev}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"

echo "=========================================="
echo "MinIO Initialization Script"
echo "=========================================="
echo ""
echo "MinIO Host: $MINIO_HOST"
echo "Bucket: $BUCKET_NAME"
echo "Frontend URL: $FRONTEND_URL"
echo ""

# Wait for MinIO to be ready
echo "Waiting for MinIO to be ready..."
for i in {1..30}; do
  if mc alias list local &> /dev/null; then
    echo "✓ MinIO is ready"
    break
  fi
  echo "Attempt $i/30..."
  sleep 2
done

# Set MinIO alias
echo "Setting MinIO alias..."
mc alias set local http://$MINIO_HOST $MINIO_ACCESS_KEY $MINIO_SECRET_KEY

# Create bucket
echo "Creating bucket '$BUCKET_NAME'..."
if mc ls local/$BUCKET_NAME &> /dev/null; then
  echo "✓ Bucket '$BUCKET_NAME' already exists"
else
  mc mb local/$BUCKET_NAME
  echo "✓ Bucket '$BUCKET_NAME' created"
fi

# Configure CORS policy
echo "Configuring CORS policy..."

# Create CORS JSON policy
CORS_POLICY=$(cat <<EOF
[
  {
    "AllowedHeaders": [
      "*"
    ],
    "AllowedMethods": [
      "GET",
      "PUT",
      "POST",
      "DELETE",
      "HEAD"
    ],
    "AllowedOrigins": [
      "$FRONTEND_URL",
      "http://localhost:3000",
      "http://localhost:5173",
      "http://frontend:5173"
    ],
    "ExposeHeaders": [
      "ETag",
      "x-amz-version-id"
    ],
    "MaxAgeSeconds": 3000
  }
]
EOF
)

# Write CORS policy to temp file
echo "$CORS_POLICY" > /tmp/cors.json

# Apply CORS policy
mc cors set local/$BUCKET_NAME /tmp/cors.json
echo "✓ CORS policy applied"

# Set bucket versioning (optional)
echo "Enabling versioning..."
mc version enable local/$BUCKET_NAME
echo "✓ Versioning enabled"

# Set bucket lifecycle (optional - auto-delete old versions after 30 days)
echo "Setting lifecycle policy..."
LIFECYCLE_POLICY=$(cat <<EOF
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
)

echo "$LIFECYCLE_POLICY" > /tmp/lifecycle.json
mc ilm import local/$BUCKET_NAME < /tmp/lifecycle.json
echo "✓ Lifecycle policy applied"

# Verify bucket configuration
echo ""
echo "=========================================="
echo "Bucket Configuration Summary"
echo "=========================================="
echo ""
echo "Bucket: $BUCKET_NAME"
echo "Access: $(mc ls local/$BUCKET_NAME 2>&1 | head -1)"
echo ""
echo "CORS Configuration:"
mc cors get local/$BUCKET_NAME
echo ""
echo "=========================================="
echo "✓ MinIO initialization complete"
echo "=========================================="
