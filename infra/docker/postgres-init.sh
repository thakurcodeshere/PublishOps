#!/bin/bash
# ============================================================================
# PublishOps — PostgreSQL Initialization Script
# ============================================================================
# Runs on first container start to create additional databases.
# The default database ($POSTGRES_DB) is created automatically by the
# official postgres image; this script creates the Airflow metadata DB
# and any extensions needed.
# ============================================================================
set -euo pipefail

log() { echo "[postgres-init] $(date '+%Y-%m-%d %H:%M:%S') $*"; }

# ---- Create Airflow metadata database ------------------------------------
log "Creating database 'airflow' (if not exists)..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE airflow OWNER ${POSTGRES_USER}'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow')\gexec
EOSQL

# ---- Install extensions in the app database --------------------------------
log "Installing extensions in '${POSTGRES_DB}'..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";
    CREATE EXTENSION IF NOT EXISTS "btree_gin";
EOSQL

# ---- Install extensions in the airflow database ----------------------------
log "Installing extensions in 'airflow'..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "airflow" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EOSQL

log "PostgreSQL initialization complete."
