# =============================================================================
# PublishOps — ElastiCache Redis 7
# =============================================================================

# ---------------------------------------------------------------------------
# Subnet Group
# ---------------------------------------------------------------------------
resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.name_prefix}-redis-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${local.name_prefix}-redis-subnet-group"
  }
}

# ---------------------------------------------------------------------------
# Parameter Group
# ---------------------------------------------------------------------------
resource "aws_elasticache_parameter_group" "redis7" {
  family = "redis7"
  name   = "${local.name_prefix}-redis7-params"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  parameter {
    name  = "notify-keyspace-events"
    value = "Ex"  # Enable expired key events (used by BullMQ)
  }

  tags = {
    Name = "${local.name_prefix}-redis7-params"
  }
}

# ---------------------------------------------------------------------------
# ElastiCache Cluster
# ---------------------------------------------------------------------------
resource "aws_elasticache_cluster" "main" {
  cluster_id           = "${local.name_prefix}-redis"
  engine               = "redis"
  engine_version       = "7.1"
  node_type            = var.redis_node_type
  num_cache_nodes      = 1
  port                 = 6379
  parameter_group_name = aws_elasticache_parameter_group.redis7.name
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]

  # Maintenance
  maintenance_window = "Mon:05:00-Mon:06:00"

  # Snapshots
  snapshot_retention_limit = 3
  snapshot_window          = "04:00-05:00"

  # Notifications
  apply_immediately = true

  tags = {
    Name = "${local.name_prefix}-redis"
  }
}
