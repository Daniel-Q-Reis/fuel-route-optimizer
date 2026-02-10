# Fuel Route Optimizer - Project Structure

This document describes the desired file structure for the project.

```
fuel-route-optimizer/
│
├── .github/                          # (KEEP - Optional CI/CD workflows)
│   └── workflows/
│
├── docs/
│   ├── adr/                          # Architecture Decision Records
│   │   ├── 0001-python-312-django-52-choice.md
│   │   ├── 0002-external-api-strategy-rate-limiting.md
│   │   ├── 0003-driver-safety-vs-range-optimization.md
│   │   ├── 0004-route-optimization-algorithm.md
│   │   ├── 0005-spatial-queries-strategy.md
│   │   └── 0006-database-query-performance.md
│   └── DOCKER.md                     # (KEEP if exists)
│
├── logs/                             # Application logs (gitignored)
│
├── src/                              # Django project root
│   ├── config/                       # Project configuration
│   │   ├── __init__.py
│   │   ├── asgi.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   │
│   ├── fuel_stations/                # Main application
│   │   ├── management/
│   │   │   └── commands/
│   │   │       └── load_fuel_stations.py    # ETL command
│   │   │
│   │   ├── clients/
│   │   │   ├── __init__.py
│   │   │   └── openrouteservice.py          # ORS API client
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── route_optimizer.py           # Core optimization logic
│   │   │
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   └── geo.py                       # Haversine, bounding box
│   │   │
│   │   ├── tests/
│   │   │   ├── __init__.py
│   │   │   ├── test_models.py
│   │   │   ├── test_services.py
│   │   │   ├── test_api.py
│   │   │   ├── test_commands.py
│   │   │   └── test_e2e.py
│   │   │
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                        # FuelStation model
│   │   ├── serializers.py                   # DRF serializers
│   │   ├── urls.py
│   │   └── views.py                         # API views
│   │
│   └── manage.py                     # Django management script
│
├── scripts/                          # Helper scripts
│   └── setup.sh                      # (DELETE unused celery scripts)
│
├── .dockerignore
├── .env.example                      # Environment template
├── .gitattributes
├── .gitignore
├── .pre-commit-config.yaml
│
├── ARCHITECTURE.md                   # High-level architecture overview
├── docker-compose.override.yml       # Local development overrides
├── docker-compose.prod.yml           # Production configuration
├── docker-compose.yml                # Main Docker Compose
├── Dockerfile                        # Django application container
├── fuel-prices-for-be-assessment.csv # Source data (8153 stations)
│
├── LICENSE
├── Makefile                          # Development commands
├── manage.py -> src/manage.py
├── mypy.ini                          # Type checking configuration
├── nginx.conf                        # Nginx reverse proxy config
├── pyproject.toml                    # Ruff, Black configuration
├── pytest.ini                        # Pytest configuration
│
├── README.md                         # Project documentation
├── ROADMAP-EXEC.md                   # Execution roadmap (this file)
│
├── requirements-dev.in               # Development dependencies
├── requirements-dev.txt              # Pinned dev dependencies
├── requirements.in                   # Production dependencies
├── requirements.txt                  # Pinned production dependencies
│
└── fuel-route-optimizer.postman_collection.json  # Postman API tests
```

---

## 🗑️ Directories to DELETE (Not Needed for This Project)

The Cookiecutter template includes some directories that are NOT needed for this assessment:

### 1. `.devcontainer/`
**Why**: We're using Docker Compose, not VS Code devcontainers.  
**Action**: `rm -rf .devcontainer/`

### 2. `scripts/celery-*.sh` (Celery-related scripts)
**Why**: No background tasks needed for this API.  
**Files to delete**:
- `scripts/celery-beat.sh`
- `scripts/celery-worker.sh`

**Keep**:
- `scripts/setup.sh` (if it's useful for Docker setup)

### 3. Unused template files
Check and remove:
- `scripts/dev-setup.sh` (if not used)
- `scripts/docker-entrypoint.sh` (if custom entrypoint not needed)

---

## 📁 Key Directories Explained

### `docs/adr/`
Contains all Architecture Decision Records (ADRs) documenting major design choices:
- Python/Django version selection
- External API strategy
- Safety considerations
- Algorithm choice
- Database optimization

### `src/fuel_stations/`
Main Django application with clean separation:
- **models.py**: `FuelStation` model with proper indexes
- **services/**: Business logic (route optimization)
- **clients/**: External API integrations (OpenRouteService)
- **utils/**: Helper functions (Haversine, bounding box)
- **tests/**: Comprehensive test suite

### `src/config/`
Django project settings:
- **settings.py**: Database, DRF, environment config
- **urls.py**: Main URL routing

---

## 📝 Important Files

### `.env.example`
Template for environment variables:
```bash
DATABASE_URL=postgresql://user:pass@db:5432/fuel_optimizer
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1
OPENROUTESERVICE_API_KEY=your-ors-api-key
```

### `pyproject.toml`
Ruff and Black configuration:
```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.black]
line-length = 100
```

### `mypy.ini`
Strict type checking:
```ini
[mypy]
python_version = 3.12
strict = True
```

### `pytest.ini`
Test configuration:
```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.test
addopts = --cov=src/fuel_stations --cov-fail-under=94
```

---

## 🎯 File Naming Conventions

### Python Modules
- `snake_case.py` (e.g., `route_optimizer.py`)
- Class names: `PascalCase` (e.g., `RouteOptimizationService`)
- Functions: `snake_case` (e.g., `get_bounding_box()`)

### Tests
- Prefix with `test_` (e.g., `test_services.py`)
- Test functions: `test_<what_it_tests>` (e.g., `test_haversine_accuracy`)

### ADRs
- Format: `0001-short-descriptive-name.md`
- Sequential numbering starting from 0001

---

## 🚀 Quick Navigation

- **Start Coding**: `src/fuel_stations/`
- **Configure Environment**: `.env`, `docker-compose.yml`
- **Read Decisions**: `docs/adr/`
- **Run Tests**: `pytest` (from project root)
- **API Docs**: `http://localhost:8000/api/schema/swagger-ui/`

---

## 📚 Documentation Hierarchy

1. **README.md**: Quick start, overview
2. **ARCHITECTURE.md**: High-level system design
3. **ROADMAP-EXEC.md**: Phase-by-phase execution plan
4. **docs/adr/**: Detailed decision rationale
5. **Code docstrings**: Implementation details

---

## ✅ Verification Commands

Check if structure is correct:
```bash
# Verify all ADRs exist
ls docs/adr/

# Verify fuel_stations app structure
tree src/fuel_stations/

# Verify configuration files
ls -la | grep -E '(Dockerfile|docker-compose|mypy|pytest)'
```

All files should exist as documented above.
