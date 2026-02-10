"""
Test settings for Django project.

Optimized for fast, isolated testing without external dependencies.
Uses SQLite in memory and local cache to avoid Docker/Redis/PostgreSQL dependencies.
"""

import tempfile

from .base import *  # noqa: F401,F403

# Database: SQLite in memory for fast, isolated tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "OPTIONS": {
            "timeout": 20,
        },
    }
}

# Cache: Local memory cache instead of Redis
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
        "TIMEOUT": 300,
        "OPTIONS": {
            "MAX_ENTRIES": 1000,
        },
    }
}

# Session storage: database instead of cache for tests
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# Email: Use locmem backend for testing
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Password hashers: Use fast MD5 for testing (insecure but fast)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Celery: Execute tasks synchronously in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

# Security settings: Disable for testing
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False

# REST Framework: Disable throttling in tests
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
}

# Logging: Quiet logging during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "level": "ERROR",
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "ERROR",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": [],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

# Static files: Use default storage for tests
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"


# Disable migrations for faster tests (use --create-db if needed)
# This can be overridden with --migrations in pytest
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


# Uncomment to disable migrations (faster but may miss migration issues)
# MIGRATION_MODULES = DisableMigrations()

# Media files: Use temporary directory


MEDIA_ROOT = tempfile.mkdtemp()

# File upload: Allow all file types in tests
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 100  # 100MB for tests
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 100  # 100MB for tests
