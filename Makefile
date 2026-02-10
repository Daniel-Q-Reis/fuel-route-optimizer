SHELL := /bin/bash

COMPOSE_EXEC_WEB = docker-compose exec web
COMPOSE_RUN_WEB = docker-compose run --rm web

.PHONY: help build build-prod up down restart logs shell setup

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  setup          : Set up the project for the first time (build, migrate, etc.)"
	@echo "  build          : Build or rebuild development Docker services"
	@echo "  build-prod     : Build production Docker images"
	@echo "  up             : Start Docker services in the background"
	@echo "  down           : Stop Docker services"
	@echo "  restart        : Restart Docker services"
	@echo "  logs           : Follow logs from all services"
	@echo "  shell          : Open a zsh shell inside the web container"
	@echo "  test           : Run the full test suite with coverage"
	@echo "  test-fast      : Run tests, skipping slow ones"
	@echo "  test-no-cov    : Run tests without coverage"
	@echo "  lint           : Run ruff linter"
	@echo "  format         : Format code with ruff"
	@echo "  typecheck      : Run mypy for static type checking"
	@echo "  security-scan  : Run bandit for security scanning"
	@echo "  quality        : Run all quality checks (lint, format, typecheck, test)"
	@echo "  migrate        : Apply database migrations"
	@echo "  migrations     : Create new database migrations"
	@echo "  superuser      : Create a new superuser"
	@echo "  collectstatic  : Collect static files for production"

# ------------------------------------------------------------------------------
# Environment Setup
# ------------------------------------------------------------------------------

setup:
	@echo "Setting up the development environment..."
	@echo "Creating .env file from .env.example if it does not exist..."
ifeq ($(OS),Windows_NT)
	@if not exist .env (copy .env.example .env && echo .env file created.)
else
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo ".env file created."; \
	else \
		echo ".env file already exists."; \
	fi
endif
	@make build
	@make up
	@echo "Waiting for services to be healthy..."
	@python -c "import time; time.sleep(5)"
	@make migrate
	@echo "Setup complete! Application is running."
	@echo "Access the API at http://127.0.0.1:8000/api/docs/"

# ------------------------------------------------------------------------------
# Docker Compose Commands
# ------------------------------------------------------------------------------

build:
	@echo "Building development Docker images..."
	docker-compose build

build-prod:
	@echo "Building production Docker images..."
	docker-compose -f docker-compose.prod.yml build

up:
	@echo "Starting Docker services..."
	docker-compose up -d


down:
	@echo "Stopping Docker services..."
	docker-compose down

restart: down up

logs:
	@echo "Following logs..."
	docker-compose logs -f

shell:
	@echo "Opening zsh shell in web container..."
	${COMPOSE_EXEC_WEB} zsh

# ------------------------------------------------------------------------------
# Quality & Testing Commands
# ------------------------------------------------------------------------------

test:
	@echo "Running tests with coverage..."
	${COMPOSE_EXEC_WEB} bash ./scripts/test.sh

test-fast:
	@echo "Running fast tests..."
	${COMPOSE_EXEC_WEB} bash ./scripts/test.sh --fast

test-no-cov:
	@echo "Running tests without coverage..."
	${COMPOSE_EXEC_WEB} bash ./scripts/test.sh --no-cov

lint:
	@echo "Running ruff linter..."
	${COMPOSE_EXEC_WEB} ruff check .

format:
	@echo "Formatting code with ruff..."
	${COMPOSE_EXEC_WEB} ruff format .

typecheck:
	@echo "Running mypy type checker..."
	${COMPOSE_EXEC_WEB} mypy src/

security-scan:
	@echo "Running bandit security scan..."
	${COMPOSE_EXEC_WEB} bandit -c pyproject.toml -r src/

quality: lint format typecheck test

# ------------------------------------------------------------------------------
# Django Management Commands
# ------------------------------------------------------------------------------

migrate:
	@echo "Applying database migrations..."
	${COMPOSE_EXEC_WEB} python manage.py migrate

migrations:
	@echo "Creating new database migrations..."
	${COMPOSE_EXEC_WEB} python manage.py makemigrations

superuser:
	@echo "Creating superuser..."
	${COMPOSE_EXEC_WEB} python manage.py createsuperuser

collectstatic:
	@echo "Collecting static files..."
	${COMPOSE_EXEC_WEB} python manage.py collectstatic --noinput
