# =============================================================================
# PublishOps — Terraform Variables
# =============================================================================

# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------
variable "project_name" {
  description = "Project name used as prefix for all resources"
  type        = string
  default     = "publishops"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

# ---------------------------------------------------------------------------
# Networking
# ---------------------------------------------------------------------------
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

# ---------------------------------------------------------------------------
# EC2
# ---------------------------------------------------------------------------
variable "instance_type" {
  description = "EC2 instance type for the application server"
  type        = string
  default     = "t3.medium"
}

variable "key_pair_name" {
  description = "Name of the EC2 key pair for SSH access"
  type        = string
  default     = "publishops-key"
}

# ---------------------------------------------------------------------------
# RDS
# ---------------------------------------------------------------------------
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "publishops"
}

variable "db_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "publishops"
  sensitive   = true
}

variable "db_password" {
  description = "PostgreSQL master password"
  type        = string
  sensitive   = true
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

# ---------------------------------------------------------------------------
# ElastiCache
# ---------------------------------------------------------------------------
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

# ---------------------------------------------------------------------------
# S3
# ---------------------------------------------------------------------------
variable "s3_bucket_name" {
  description = "S3 bucket name for media storage"
  type        = string
  default     = "publishops-media"
}

# ---------------------------------------------------------------------------
# Lambda
# ---------------------------------------------------------------------------
variable "lambda_memory_size" {
  description = "Lambda function memory in MB"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 300
}

# ---------------------------------------------------------------------------
# API Keys (sensitive)
# ---------------------------------------------------------------------------
variable "anthropic_api_key" {
  description = "Anthropic Claude API key for content generation"
  type        = string
  default     = ""
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key (fallback content generation)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "app_secret_key" {
  description = "Application secret key for JWT signing"
  type        = string
  sensitive   = true
}
