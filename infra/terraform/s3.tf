# =============================================================================
# PublishOps — S3 Media Storage
# =============================================================================

# ---------------------------------------------------------------------------
# S3 Bucket
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "media" {
  bucket = var.s3_bucket_name

  tags = {
    Name = "${local.name_prefix}-media"
  }
}

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
resource "aws_s3_bucket_versioning" "media" {
  bucket = aws_s3_bucket.media.id

  versioning_configuration {
    status = "Enabled"
  }
}

# ---------------------------------------------------------------------------
# Server-Side Encryption
# ---------------------------------------------------------------------------
resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# ---------------------------------------------------------------------------
# Block Public Access
# ---------------------------------------------------------------------------
resource "aws_s3_bucket_public_access_block" "media" {
  bucket = aws_s3_bucket.media.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ---------------------------------------------------------------------------
# Lifecycle Rules
# ---------------------------------------------------------------------------
resource "aws_s3_bucket_lifecycle_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  # Rule 1: raw/ — move to IA after 30 days, Glacier after 90 days
  rule {
    id     = "raw-storage-tiering"
    status = "Enabled"

    filter {
      prefix = "raw/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = 180
    }
  }

  # Rule 2: tmp/ — delete after 7 days
  rule {
    id     = "tmp-cleanup"
    status = "Enabled"

    filter {
      prefix = "tmp/"
    }

    expiration {
      days = 7
    }

    noncurrent_version_expiration {
      noncurrent_days = 1
    }
  }

  # Rule 3: processed/ — move to IA after 60 days
  rule {
    id     = "processed-tiering"
    status = "Enabled"

    filter {
      prefix = "processed/"
    }

    transition {
      days          = 60
      storage_class = "STANDARD_IA"
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }

  # Rule 4: Clean up incomplete multipart uploads
  rule {
    id     = "abort-incomplete-multipart"
    status = "Enabled"

    filter {
      prefix = ""
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 3
    }
  }
}

# ---------------------------------------------------------------------------
# CORS Configuration (for dashboard access)
# ---------------------------------------------------------------------------
resource "aws_s3_bucket_cors_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST"]
    allowed_origins = [
      "http://localhost:3000",
      "https://*.publishops.io",
    ]
    expose_headers  = ["ETag", "Content-Length", "Content-Type"]
    max_age_seconds = 3600
  }
}

# ---------------------------------------------------------------------------
# Bucket Policy
# ---------------------------------------------------------------------------
resource "aws_s3_bucket_policy" "media" {
  bucket = aws_s3_bucket.media.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnforceTLS"
        Effect = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.media.arn,
          "${aws_s3_bucket.media.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid    = "AllowEC2Access"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.ec2.arn
        }
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.media.arn,
          "${aws_s3_bucket.media.arn}/*"
        ]
      },
      {
        Sid    = "AllowLambdaRead"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.lambda_execution.arn
        }
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.media.arn,
          "${aws_s3_bucket.media.arn}/*"
        ]
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.media]
}
