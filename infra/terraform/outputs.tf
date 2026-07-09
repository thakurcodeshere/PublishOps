# =============================================================================
# PublishOps — Terraform Outputs
# =============================================================================

# ---------------------------------------------------------------------------
# VPC
# ---------------------------------------------------------------------------
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

# ---------------------------------------------------------------------------
# EC2
# ---------------------------------------------------------------------------
output "ec2_instance_id" {
  description = "ID of the application EC2 instance"
  value       = aws_instance.app.id
}

output "ec2_public_ip" {
  description = "Elastic IP address of the application server"
  value       = aws_eip.app.public_ip
}

output "app_url" {
  description = "URL for the FastAPI backend"
  value       = "http://${aws_eip.app.public_ip}:8000"
}

output "dashboard_url" {
  description = "URL for the Next.js dashboard"
  value       = "http://${aws_eip.app.public_ip}:3000"
}

output "airflow_url" {
  description = "URL for the Airflow webserver"
  value       = "http://${aws_eip.app.public_ip}:8080"
}

# ---------------------------------------------------------------------------
# RDS
# ---------------------------------------------------------------------------
output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint (host:port)"
  value       = aws_db_instance.main.endpoint
}

output "rds_hostname" {
  description = "RDS PostgreSQL hostname"
  value       = aws_db_instance.main.address
}

output "rds_port" {
  description = "RDS PostgreSQL port"
  value       = aws_db_instance.main.port
}

output "database_url" {
  description = "Full PostgreSQL connection URL"
  value       = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${aws_db_instance.main.address}:${aws_db_instance.main.port}/${var.db_name}"
  sensitive   = true
}

# ---------------------------------------------------------------------------
# ElastiCache
# ---------------------------------------------------------------------------
output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_cluster.main.cache_nodes[0].address
}

output "redis_port" {
  description = "ElastiCache Redis port"
  value       = aws_elasticache_cluster.main.cache_nodes[0].port
}

output "redis_url" {
  description = "Full Redis connection URL"
  value       = "redis://${aws_elasticache_cluster.main.cache_nodes[0].address}:${aws_elasticache_cluster.main.cache_nodes[0].port}/0"
}

# ---------------------------------------------------------------------------
# S3
# ---------------------------------------------------------------------------
output "s3_bucket_name" {
  description = "S3 media bucket name"
  value       = aws_s3_bucket.media.bucket
}

output "s3_bucket_arn" {
  description = "S3 media bucket ARN"
  value       = aws_s3_bucket.media.arn
}

output "s3_bucket_regional_domain" {
  description = "S3 bucket regional domain name"
  value       = aws_s3_bucket.media.bucket_regional_domain_name
}

# ---------------------------------------------------------------------------
# Lambda
# ---------------------------------------------------------------------------
output "lambda_function_name" {
  description = "Upload burst Lambda function name"
  value       = aws_lambda_function.upload_burst.function_name
}

output "lambda_function_arn" {
  description = "Upload burst Lambda function ARN"
  value       = aws_lambda_function.upload_burst.arn
}

# ---------------------------------------------------------------------------
# Security Groups
# ---------------------------------------------------------------------------
output "app_security_group_id" {
  description = "Application server security group ID"
  value       = aws_security_group.app.id
}

output "rds_security_group_id" {
  description = "RDS security group ID"
  value       = aws_security_group.rds.id
}

output "redis_security_group_id" {
  description = "ElastiCache Redis security group ID"
  value       = aws_security_group.redis.id
}
