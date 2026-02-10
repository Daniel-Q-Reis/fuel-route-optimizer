#!/bin/bash

# Test script for the Django Senior Template
# Runs tests with proper environment configuration

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in Docker or local environment
if [ -f /.dockerenv ]; then
    print_status "Running inside Docker container"
    PYTHON_CMD="python"
    PIP_CMD="pip"
else
    print_status "Running in local environment"
    # Try to detect Python command
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        PIP_CMD="pip3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
        PIP_CMD="pip"
    else
        print_error "Python not found. Please install Python 3.12+"
        exit 1
    fi
fi

# Set Django settings for tests (CRITICAL FIX)
export DJANGO_SETTINGS_MODULE=src.fuel-route-optimizer.settings.test

print_status "Using Django settings: $DJANGO_SETTINGS_MODULE"
print_status "Python command: $PYTHON_CMD"

# Check if Django can import settings
if ! $PYTHON_CMD -c "from django.conf import settings; print('Settings OK:', settings.DATABASES['default']['ENGINE'])" 2>/dev/null; then
    print_error "Django settings configuration failed!"
    print_error "Make sure you're in the project root directory with manage.py"
    exit 1
fi

# Check if pytest is available
if ! $PYTHON_CMD -c "import pytest" &> /dev/null; then
    print_warning "pytest not found. Installing test dependencies..."
    $PIP_CMD install pytest pytest-django pytest-cov
fi

# Check if we need to install dependencies
if [ ! -f "/.dockerenv" ] && [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    print_warning "No virtual environment detected. Consider creating one:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
fi

# Parse command line arguments
COVERAGE=true
FAST=false
VERBOSE=false
TEST_PATH="src"

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cov|--no-coverage)
            COVERAGE=false
            shift
            ;;
        --fast)
            FAST=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --path)
            TEST_PATH="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --no-cov, --no-coverage    Disable coverage reporting"
            echo "  --fast                      Run fast tests only (exclude slow marker)"
            echo "  -v, --verbose              Verbose output"
            echo "  --path PATH                 Run tests in specific path"
            echo "  -h, --help                 Show this help message"
            echo ""
            echo "Environment:"
            echo "  DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE"
            exit 0
            ;;
        *)
            TEST_PATH="$1"
            shift
            ;;
    esac
done

# Build pytest command
PYTEST_ARGS=""

if [ "$COVERAGE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS --cov=src --cov-report=term-missing --cov-report=html"
fi

if [ "$FAST" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS -m 'not slow'"
fi

if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS -v"
else
    PYTEST_ARGS="$PYTEST_ARGS -q"
fi

# Add test path
PYTEST_ARGS="$PYTEST_ARGS $TEST_PATH"

print_status "Running tests with command: pytest$PYTEST_ARGS"
print_status "Test settings configured for fast, isolated testing"
print_status "Database: SQLite in-memory"
print_status "Cache: Local memory"
print_status "Celery: Eager mode"
print_status "Settings module: $DJANGO_SETTINGS_MODULE"

# Verify Django setup before running tests
print_status "Verifying Django configuration..."
if ! $PYTHON_CMD -c "import django; django.setup(); from django.conf import settings; print('✓ Django setup successful')" 2>/dev/null; then
    print_error "Django setup failed. Check your DJANGO_SETTINGS_MODULE configuration."
    exit 1
fi

# Run tests
print_status "Starting test execution..."
if $PYTHON_CMD -m pytest $PYTEST_ARGS; then
    print_success "All tests passed!"

    if [ "$COVERAGE" = true ]; then
        print_status "Coverage report generated in htmlcov/index.html"
        # Show coverage summary
        if command -v coverage &> /dev/null; then
            echo ""
            coverage report --show-missing
        fi
    fi

    exit 0
else
    print_error "Some tests failed. Check the output above for details."
    print_error "Common issues:"
    print_error "  - Make sure DJANGO_SETTINGS_MODULE is set correctly"
    print_error "  - Verify you're in the project root directory"
    print_error "  - Check that src/fuel-route-optimizer/settings/test.py exists"
    exit 1
fi
