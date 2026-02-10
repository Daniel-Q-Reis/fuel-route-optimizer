#!/usr/bin/env bash
set -Eeuo pipefail

# Colors for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[entrypoint]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[entrypoint] ✅${NC} $1"
}

log_error() {
    echo -e "${RED}[entrypoint] ❌${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[entrypoint] ⚠️${NC} $1"
}

# Configuration from environment variables
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"
DB_NAME="${DB_NAME:-master_template_db}"

# Debugging configuration
DEBUGPY="${DEBUGPY:-0}"
DEBUGPY_WAIT_FOR_CLIENT="${DEBUGPY_WAIT_FOR_CLIENT:-0}"
DEBUGPY_HOST="${DEBUGPY_HOST:-0.0.0.0}"
DEBUGPY_PORT="${DEBUGPY_PORT:-5678}"

# Set PGPASSWORD for psql commands
export PGPASSWORD="${DB_PASSWORD}"

log "Starting Django Master Template container..."
log "Database: ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

wait_for_postgres() {
    log "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."

    local max_attempts=60
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "postgres" >/dev/null 2>&1; then
            log_success "PostgreSQL is ready!"
            return 0
        fi

        attempt=$((attempt + 1))
        if [ $((attempt % 10)) -eq 0 ]; then
            log "Still waiting for PostgreSQL... (attempt $attempt/$max_attempts)"
        fi
        sleep 2
    done

    log_error "Timeout waiting for PostgreSQL after $((max_attempts * 2)) seconds"
    exit 1
}

create_database_if_needed() {
    log "Checking if database '${DB_NAME}' exists..."

    # Check if database exists
    if psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "postgres" \
        -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" 2>/dev/null | grep -q 1; then
        log_success "Database '${DB_NAME}' already exists"
    else
        log "Creating database '${DB_NAME}'..."
        if psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "postgres" \
            -c "CREATE DATABASE \"${DB_NAME}\" OWNER \"${DB_USER}\";" >/dev/null 2>&1; then
            log_success "Database '${DB_NAME}' created successfully"
        else
            log_error "Failed to create database '${DB_NAME}'"
            exit 1
        fi
    fi
}

run_migrations() {
    log "Running Django migrations..."
    log "DEBUG: DJANGO_SETTINGS_MODULE is set to ${DJANGO_SETTINGS_MODULE:-<not_set>}"

    if python manage.py migrate --noinput; then
        log_success "Migrations completed successfully"
    else
        log_error "Migrations failed"
        exit 1
    fi
}

collect_static_files() {
    if [[ "${COLLECTSTATIC:-0}" == "1" ]]; then
        log "Collecting static files..."
        if python manage.py collectstatic --noinput; then
            log_success "Static files collected successfully"
        else
            log_warning "Static files collection failed (non-critical)"
        fi
    fi
}

create_superuser_if_needed() {
    log "Creating default superuser if needed..."

    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@localhost', 'admin123')
    print('✅ Superuser created: admin/admin123')
else:
    print('ℹ️  Superuser already exists')
" 2>/dev/null || log_warning "Could not create/check superuser (non-critical)"
}

start_django_server() {
    if [[ "${DEBUGPY}" == "1" ]]; then
        log "Starting Django with debugpy on ${DEBUGPY_HOST}:${DEBUGPY_PORT}"
        log "VS Code can attach to debugpy for remote debugging"

        if [[ "${DEBUGPY_WAIT_FOR_CLIENT}" == "1" ]]; then
            log_warning "Waiting for debugger client to attach..."
        fi

        wait_for_client_arg=()
        if [[ "${DEBUGPY_WAIT_FOR_CLIENT}" == "1" ]]; then
            wait_for_client_arg+=(--wait-for-client)
        fi

        exec python -m debugpy \
            --listen "${DEBUGPY_HOST}:${DEBUGPY_PORT}" \
            "${wait_for_client_arg[@]}" \
            manage.py runserver 0.0.0.0:8000
    else
        log "Starting Django development server..."
        exec python manage.py runserver 0.0.0.0:8000
    fi
}

# Main execution flow
main() {
    # Fix file ownership in mounted volume
    if [ -d ".git" ]; then
        log "Fixing .git directory ownership..."
        chown -R appuser:appuser .git || log_warning "Could not change .git ownership. Pre-commit might fail."
    fi

    wait_for_postgres
    create_database_if_needed
    run_migrations
    collect_static_files
    create_superuser_if_needed

    log_success "Django setup completed successfully!"
    log "🌟 Access your application at: http://localhost:8000"
    log "🔐 Admin panel: http://localhost:8000/admin/ (admin/admin123)"

    start_django_server
}

# Handle signals gracefully
trap 'log_warning "Received shutdown signal, stopping gracefully..."; exit 0' SIGTERM SIGINT

# Run main function
main "$@"
