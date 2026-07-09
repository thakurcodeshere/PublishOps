#!/usr/bin/env bash
# =============================================================================
# PublishOps — Setup Script
# =============================================================================
# Automated setup for the local development environment.
# Checks prerequisites, starts services, seeds databases.
#
# Usage:
#   chmod +x infra/scripts/setup.sh
#   ./infra/scripts/setup.sh
# =============================================================================
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log()   { echo -e "${BLUE}[PublishOps]${NC} $*"; }
ok()    { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*"; }

# Navigate to project root (relative to this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "============================================="
echo "  PublishOps — Development Setup"
echo "============================================="
echo ""

# ---- 1. Check Prerequisites ------------------------------------------------
log "Checking prerequisites..."

# Docker
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | grep -oP '\d+\.\d+\.\d+' | head -1)
    ok "Docker ${DOCKER_VERSION}"
else
    error "Docker is not installed. Please install Docker Desktop from https://docker.com"
    exit 1
fi

# Docker Compose
if docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version --short 2>/dev/null || docker compose version | grep -oP '\d+\.\d+\.\d+' | head -1)
    ok "Docker Compose ${COMPOSE_VERSION}"
else
    error "Docker Compose is not available. Please install Docker Compose v2."
    exit 1
fi

# Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    NODE_MAJOR=$(echo "$NODE_VERSION" | grep -oP '\d+' | head -1)
    if [ "$NODE_MAJOR" -ge 20 ]; then
        ok "Node.js ${NODE_VERSION}"
    else
        warn "Node.js ${NODE_VERSION} found but 20+ is recommended"
    fi
else
    warn "Node.js not found — needed for running workers locally outside Docker"
fi

# Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | grep -oP '\d+\.\d+' | head -1)
    ok "Python ${PYTHON_VERSION}"
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version | grep -oP '\d+\.\d+' | head -1)
    ok "Python ${PYTHON_VERSION}"
else
    warn "Python not found — needed for running seed scripts locally"
fi

echo ""

# ---- 2. Environment File ---------------------------------------------------
log "Setting up environment..."

if [ ! -f .env ]; then
    cp .env.example .env
    ok "Created .env from .env.example"
    warn "Please review .env and update API keys before proceeding to production"
else
    ok ".env already exists — skipping"
fi

echo ""

# ---- 3. Start Services -----------------------------------------------------
log "Starting services with Docker Compose..."

docker compose pull --ignore-pull-failures 2>/dev/null || true
docker compose up -d --build

ok "Docker Compose services started"
echo ""

# ---- 4. Wait for Services --------------------------------------------------
log "Waiting for services to be healthy..."

wait_for_service() {
    local service=$1
    local max_wait=$2
    local elapsed=0

    while [ $elapsed -lt $max_wait ]; do
        STATUS=$(docker compose ps --format json "$service" 2>/dev/null | grep -o '"Health":"[^"]*"' | head -1 || echo "")
        if echo "$STATUS" | grep -q "healthy"; then
            ok "$service is healthy"
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done

    warn "$service did not become healthy within ${max_wait}s (may still be starting)"
    return 0
}

wait_for_service "postgres" 60
wait_for_service "redis" 30
wait_for_service "backend" 90

echo ""

# ---- 5. Wait for Airflow Init ----------------------------------------------
log "Waiting for Airflow initialization..."

AIRFLOW_INIT_TIMEOUT=120
ELAPSED=0
while [ $ELAPSED -lt $AIRFLOW_INIT_TIMEOUT ]; do
    INIT_STATUS=$(docker compose ps --format json "airflow-init" 2>/dev/null | grep -o '"State":"[^"]*"' | head -1 || echo "")
    if echo "$INIT_STATUS" | grep -q "exited"; then
        ok "Airflow initialization complete"
        break
    fi
    sleep 3
    ELAPSED=$((ELAPSED + 3))
done

if [ $ELAPSED -ge $AIRFLOW_INIT_TIMEOUT ]; then
    warn "Airflow init timed out — check logs with: docker compose logs airflow-init"
fi

echo ""

# ---- 6. Seed Database -------------------------------------------------------
log "Seeding database..."

# Install psycopg2 if needed
pip3 install --quiet psycopg2-binary 2>/dev/null || pip install --quiet psycopg2-binary 2>/dev/null || warn "Could not install psycopg2-binary"

# Export DB connection for seed scripts
export POSTGRES_HOST=localhost
export POSTGRES_PORT=${POSTGRES_PORT:-5432}
export POSTGRES_USER=${POSTGRES_USER:-publishops}
export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changeme_in_production_2024!}
export POSTGRES_DB=${POSTGRES_DB:-publishops}

# Seed hooks
if python3 infra/scripts/seed_hooks.py 2>/dev/null || python infra/scripts/seed_hooks.py 2>/dev/null; then
    ok "Hooks library seeded"
else
    warn "Failed to seed hooks — you can retry with: python3 infra/scripts/seed_hooks.py"
fi

# Seed platform rules
if python3 infra/scripts/seed_platform_rules.py 2>/dev/null || python infra/scripts/seed_platform_rules.py 2>/dev/null; then
    ok "Platform rules seeded"
else
    warn "Failed to seed platform rules — you can retry with: python3 infra/scripts/seed_platform_rules.py"
fi

echo ""

# ---- 7. Summary -------------------------------------------------------------
echo "============================================="
echo ""
echo -e "${GREEN}  PublishOps is ready! 🚀${NC}"
echo ""
echo "  Access your services:"
echo ""
echo -e "  ${BLUE}Dashboard${NC}      http://localhost:3000"
echo -e "  ${BLUE}Backend API${NC}    http://localhost:8000"
echo -e "  ${BLUE}API Docs${NC}       http://localhost:8000/docs"
echo -e "  ${BLUE}Airflow${NC}        http://localhost:8080"
echo -e "  ${BLUE}PostgreSQL${NC}     localhost:5432"
echo -e "  ${BLUE}Redis${NC}          localhost:6379"
echo ""
echo "  Airflow credentials:"
echo -e "    User:     ${YELLOW}admin${NC}"
echo -e "    Password: ${YELLOW}admin${NC}"
echo ""
echo "  Useful commands:"
echo "    docker compose logs -f backend    # Tail backend logs"
echo "    docker compose logs -f airflow-scheduler  # Tail scheduler"
echo "    docker compose restart backend    # Restart a service"
echo "    docker compose down               # Stop all services"
echo "    docker compose down -v            # Stop + remove volumes"
echo ""
echo "============================================="
