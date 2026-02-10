# mypy: ignore-errors
from typing import cast

from decouple import Csv, config

# Imports for optional features

import logging  # noqa: F401
import sentry_sdk  # noqa: F401
from sentry_sdk.integrations.django import DjangoIntegration  # noqa: F401
from sentry_sdk.integrations.logging import LoggingIntegration  # noqa: F401
from sentry_sdk.integrations.redis import RedisIntegration  # noqa: F401
from sentry_sdk.integrations.celery import CeleryIntegration  # noqa: F401


from .base import *  # noqa: F403, F401

# Import specific symbols to avoid F405 errors
from .base import (
    CACHES,
    DATABASES,
    INSTALLED_APPS,
    LOGGING,
    MIDDLEWARE,
    REST_FRAMEWORK,
    VERSION,  # noqa: F401
)

# GENERAL
# ------------------------------------------------------------------------------
DEBUG = False
ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())

# SECURITY
# ------------------------------------------------------------------------------
# SSL/TLS Settings
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# HSTS Settings
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'",)

# Database Performance
# ------------------------------------------------------------------------------
DATABASES["default"]["CONN_MAX_AGE"] = 600  # 10 minutes
DATABASES["default"]["OPTIONS"] = {
    "MAX_CONNS": 20,
    "MIN_CONNS": 5,
}

# Static Files Optimization
# ------------------------------------------------------------------------------
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = False

# Cache optimization for production
# ------------------------------------------------------------------------------
CACHES["default"]["TIMEOUT"] = 3600  # type: ignore[index]
connection_pool_kwargs = CACHES["default"]["OPTIONS"]["CONNECTION_POOL_KWARGS"]  # type: ignore[index]
connection_pool_kwargs.update(
    {
        "max_connections": 100,  # Higher for production
        "retry_on_timeout": True,
    }
)
# Disable IGNORE_EXCEPTIONS in production for better error visibility
CACHES["default"]["OPTIONS"]["IGNORE_EXCEPTIONS"] = False  # type: ignore[index]

# Email Configuration
# ------------------------------------------------------------------------------
EMAIL_BACKEND = config(
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = config("EMAIL_HOST")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL")
SERVER_EMAIL = config("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)

# Logging for Production
# ------------------------------------------------------------------------------
LOGGING["handlers"]["file"] = {
    "level": "ERROR",
    "class": "logging.handlers.RotatingFileHandler",
    "filename": "logs/production.log",
    "maxBytes": 1024 * 1024 * 15,  # 15MB
    "backupCount": 10,
    "formatter": "json",
}

# Add file handler to root logger
root_handlers = LOGGING["root"]["handlers"]  # type: ignore[index]
root_handlers.append("file")

# Error Monitoring with Sentry (Senior-level integration)
# ------------------------------------------------------------------------------
SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    # Configure logging integration for better error context
    sentry_logging = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR,  # Send errors as events
    )

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(
                transaction_style="url",
                middleware_spans=True,
                signals_spans=False,
            ),
            CeleryIntegration(
                monitor_beat_tasks=True,
                propagate_traces=True,
            ),
            RedisIntegration(),
            sentry_logging,
        ],
        # Performance Monitoring
        traces_sample_rate=config("SENTRY_TRACES_SAMPLE_RATE", default=0.1, cast=float),
        profiles_sample_rate=config(
            "SENTRY_PROFILES_SAMPLE_RATE", default=0.1, cast=float
        ),
        # Privacy Settings
        send_default_pii=False,
        # Environment and Release Tracking
        environment=config("ENVIRONMENT", default="production"),
        release=VERSION,
        # Custom Error Filtering
        before_send=lambda event, hint: event
        if event.get("level") != "debug"
        else None,
        # Performance tuning
        max_breadcrumbs=50,
        attach_stacktrace=True,
    )


# Celery Production Settings (Senior-level optimizations)
# ------------------------------------------------------------------------------
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Task retry configuration
CELERY_TASK_RETRY_KWARGS = {
    "max_retries": 3,
    "countdown": 60,
}

# Worker optimization
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True

# API Rate Limiting (more restrictive in production)
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    "anon": "50/hour",
    "user": "500/hour",
    "login": "5/min",  # Rate limit login attempts
    "register": "3/min",  # Rate limit registration
}

# Add custom throttle classes
throttle_classes = cast(list[str], REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"])
throttle_classes.extend(
    [
        "rest_framework.throttling.ScopedRateThrottle",
    ]
)

# File Upload Security
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_PERMISSIONS = 0o644

# Session Security (Senior-level configuration)
SESSION_COOKIE_AGE = 1800  # 30 minutes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# CSRF Protection
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", cast=Csv(), default=[])

# Additional Security Headers
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# CORS Security for production
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", cast=Csv())
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = ["Content-Disposition"]

# Database connection pooling (if using pgbouncer)
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True

# Admin Security
ADMIN_URL = config("ADMIN_URL", default="admin/")

# Health Check Configuration
HEALTH_CHECK = {
    "DISK_USAGE_MAX": 90,  # percent
    "MEMORY_MIN": 100,  # MB
}

# Performance monitoring
INSTALLED_APPS.extend(
    [
        # Add django-extensions for production profiling if needed
        # 'django_extensions',
    ]
)

# Middleware optimization for production
MIDDLEWARE.insert(1, "django.middleware.cache.UpdateCacheMiddleware")
MIDDLEWARE.append("django.middleware.cache.FetchFromCacheMiddleware")
