# Docker Setup Guide

This guide provides instructions for setting up and running the project using Docker.

## Prerequisites

- Docker Desktop (version 4.0+)
- Docker Compose (version 2.0+)
- Git
- 4GB of available RAM
- 2GB of available disk space

## 🚀 Quick Start (Recommended)

### 1. Clone and Configure

```bash
git clone https://github.com/your-username/your-project.git
cd your-project
```

### 2. Automated Setup

```bash
# Run the full setup with a single command
make setup
```

This command will:
- Build the Docker images.
- Start the services.
- Create a `.env` file from the example.
- Apply database migrations.

### 3. Access the Application

Once the script is finished, you can access the following services:

- **Application**: [http://localhost:8000](http://localhost:8000)
- **Django Admin**: [http://localhost:8000/admin/](http://localhost:8000/admin/)
  - **User**: `admin`
  - **Password**: `admin123` (or as defined in your `.env` file)
- **API Documentation**: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)
- **PostgreSQL**: `localhost:5432`
- **Redis**: `localhost:6379`

## 🔧 Manual Setup (Alternative)

If you prefer to set up the environment step-by-step:

```bash
# Clean up previous containers (if they exist)
docker-compose down -v

# Build the images
docker-compose build --no-cache

# Start the services
docker-compose up -d

# Check the logs
docker-compose logs -f web
```

## 🚫 Troubleshooting

### ❌ Error: "database does not exist"

**Quick Fix:**
```bash
make down && make up
```

**Manual Fix:**
```bash
# 1. Stop all services
docker-compose down -v

# 2. Remove the database volume
docker volume rm your-project_db-data

# 3. Rebuild and restart
docker-compose build --no-cache db
docker-compose up -d
```

### ❌ Docker Build Errors

```bash
# 1. Prune the Docker system to remove old images and build cache
docker system prune -a

# 2. Re-run the setup
make setup
```

### ❌ Slow Performance on Windows

1.  **Use WSL2:**
    - Configure Docker Desktop to use the WSL2-based engine.
    - Clone the project inside your WSL2 environment.
    - Run all Docker commands from within WSL2.

2.  **Optimize Docker Desktop:**
    - Allocate more memory (4GB+) to Docker in the settings.

## 📊 Useful Commands

### Container Management

```bash
# Stop all services
make down

# Restart a specific service
docker-compose restart web

# Check the status of the containers
docker-compose ps

# View real-time logs
make logs
```

### Django Management

```bash
# Open a Django shell
make shell

# Create new database migrations
make migrations

# Apply database migrations
make migrate

# Create a superuser
make superuser

# Collect static files
make collectstatic

# Run tests
make test
```

### Monitoring

```bash
# Check resource usage
docker stats

# Enter a running container
docker-compose exec web bash
```
