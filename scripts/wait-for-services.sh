#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
HOST=""
PORT=""
SERVICE=""
TIMEOUT=60
QUIET=false

usage() {
    echo "Usage: $0 -h HOST -p PORT -s SERVICE_NAME [-t TIMEOUT] [-q]"
    echo "  -h HOST: hostname to connect to"
    echo "  -p PORT: port to connect to"
    echo "  -s SERVICE: service name for logging"
    echo "  -t TIMEOUT: timeout in seconds (default: 60)"
    echo "  -q: quiet mode"
    echo ""
    echo "Examples:"
    echo "  $0 -h db -p 5432 -s PostgreSQL"
    echo "  $0 -h redis -p 6379 -s Redis"
    exit 1
}

log() {
    if [ "$QUIET" != "true" ]; then
        echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
    fi
}

log_success() {
    if [ "$QUIET" != "true" ]; then
        echo -e "${GREEN}[$(date +'%H:%M:%S')] ✅ $1${NC}"
    fi
}

log_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ❌ $1${NC}" >&2
}

log_warning() {
    if [ "$QUIET" != "true" ]; then
        echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️  $1${NC}"
    fi
}

# Parse command line arguments
while getopts "h:p:s:t:q" opt; do
    case $opt in
        h) HOST="$OPTARG" ;;
        p) PORT="$OPTARG" ;;
        s) SERVICE="$OPTARG" ;;
        t) TIMEOUT="$OPTARG" ;;
        q) QUIET=true ;;
        *) usage ;;
    esac
done

# Validate required arguments
if [ -z "$HOST" ] || [ -z "$PORT" ] || [ -z "$SERVICE" ]; then
    log_error "Missing required arguments"
    usage
fi

# Validate timeout is a number
if ! [[ "$TIMEOUT" =~ ^[0-9]+$ ]]; then
    log_error "Timeout must be a positive integer"
    exit 1
fi

log "Waiting for $SERVICE at $HOST:$PORT..."
log "Timeout set to ${TIMEOUT} seconds"

start_time=$(date +%s)
end_time=$((start_time + TIMEOUT))

while [ $(date +%s) -lt $end_time ]; do
    if nc -z "$HOST" "$PORT" 2>/dev/null; then
        elapsed=$(($(date +%s) - start_time))
        log_success "$SERVICE is ready! (took ${elapsed}s)"
        exit 0
    fi

    current_time=$(date +%s)
    remaining=$((end_time - current_time))

    if [ $((current_time % 5)) -eq 0 ] && [ "$QUIET" != "true" ]; then
        log "Still waiting for $SERVICE... (${remaining}s remaining)"
    fi

    sleep 1
done

log_error "Timeout waiting for $SERVICE at $HOST:$PORT after ${TIMEOUT} seconds"
exit 1
