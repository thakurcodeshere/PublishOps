# =============================================================================
# PublishOps — Lambda Function for Upload Bursts
# =============================================================================

# ---------------------------------------------------------------------------
# IAM Role for Lambda
# ---------------------------------------------------------------------------
resource "aws_iam_role" "lambda_execution" {
  name = "${local.name_prefix}-lambda-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# CloudWatch Logs
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# VPC access
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# S3 read access
resource "aws_iam_role_policy" "lambda_s3" {
  name = "${local.name_prefix}-lambda-s3-policy"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
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
}

# ---------------------------------------------------------------------------
# Lambda Function
# ---------------------------------------------------------------------------
data "archive_file" "lambda_upload_burst" {
  type        = "zip"
  output_path = "${path.module}/lambda_upload_burst.zip"

  source {
    content  = <<-PYTHON
import json
import os
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:8000")
API_KEY = os.environ.get("BACKEND_API_KEY", "")


def make_request(url: str, data: dict | None = None, method: str = "POST") -> dict:
    """Make an HTTP request to the backend API."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP {e.code}: {e.read().decode()}")
        raise
    except urllib.error.URLError as e:
        logger.error(f"URL Error: {e.reason}")
        raise


def handler(event, context):
    """
    Lambda handler for upload burst processing.
    Triggered every 15 minutes by EventBridge.

    Checks for pending upload jobs and processes them in burst mode,
    distributing uploads across platforms to avoid rate limits.
    """
    logger.info("Upload burst handler invoked at %s", datetime.now(timezone.utc).isoformat())
    logger.info("Event: %s", json.dumps(event))

    try:
        # 1. Check for pending uploads
        pending = make_request(f"{BACKEND_URL}/api/v1/scheduler/pending-uploads", method="GET")
        pending_count = pending.get("count", 0)

        if pending_count == 0:
            logger.info("No pending uploads found")
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "No pending uploads", "processed": 0}),
            }

        logger.info("Found %d pending uploads", pending_count)

        # 2. Process uploads in batch
        result = make_request(
            f"{BACKEND_URL}/api/v1/scheduler/process-upload-burst",
            data={
                "max_batch_size": 10,
                "respect_rate_limits": True,
                "triggered_by": "lambda_eventbridge",
                "invocation_id": context.aws_request_id,
            },
        )

        processed = result.get("processed", 0)
        failed = result.get("failed", 0)
        skipped = result.get("skipped", 0)

        logger.info(
            "Upload burst complete: processed=%d, failed=%d, skipped=%d",
            processed, failed, skipped,
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Upload burst processed",
                "processed": processed,
                "failed": failed,
                "skipped": skipped,
                "pending_remaining": pending_count - processed,
            }),
        }

    except Exception as e:
        logger.exception("Upload burst handler failed")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
PYTHON
    filename = "lambda_function.py"
  }
}

resource "aws_lambda_function" "upload_burst" {
  function_name = "${local.name_prefix}-upload-burst"
  description   = "Processes pending uploads in burst mode every 15 minutes"
  role          = aws_iam_role.lambda_execution.arn
  handler       = "lambda_function.handler"
  runtime       = "python3.12"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size

  filename         = data.archive_file.lambda_upload_burst.output_path
  source_code_hash = data.archive_file.lambda_upload_burst.output_base64sha256

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      BACKEND_URL     = "http://${aws_eip.app.public_ip}:8000"
      BACKEND_API_KEY = var.app_secret_key
      ENVIRONMENT     = var.environment
      S3_BUCKET       = aws_s3_bucket.media.bucket
    }
  }

  tags = {
    Name = "${local.name_prefix}-upload-burst"
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy_attachment.lambda_vpc,
  ]
}

# ---------------------------------------------------------------------------
# EventBridge Trigger — Every 15 minutes
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_event_rule" "upload_burst_schedule" {
  name                = "${local.name_prefix}-upload-burst-schedule"
  description         = "Trigger upload burst Lambda every 15 minutes"
  schedule_expression = "rate(15 minutes)"

  tags = {
    Name = "${local.name_prefix}-upload-burst-schedule"
  }
}

resource "aws_cloudwatch_event_target" "upload_burst" {
  rule      = aws_cloudwatch_event_rule.upload_burst_schedule.name
  target_id = "upload-burst-lambda"
  arn       = aws_lambda_function.upload_burst.arn
}

resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.upload_burst.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.upload_burst_schedule.arn
}

# ---------------------------------------------------------------------------
# CloudWatch Log Group
# ---------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "lambda_upload_burst" {
  name              = "/aws/lambda/${aws_lambda_function.upload_burst.function_name}"
  retention_in_days = 14

  tags = {
    Name = "${local.name_prefix}-upload-burst-logs"
  }
}
