"""
Health check utilities for application monitoring.

This module provides comprehensive health checks for production monitoring,
including database connectivity, cache availability, and system resources.
"""

import logging
from typing import Any

import psutil
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


class HealthCheckStatus:
    """Health check status constants."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class HealthChecker:
    """Comprehensive health checker for application components."""

    def __init__(self) -> None:
        self.checks = {
            "database": self._check_database,
            "cache": self._check_cache,
            "disk_space": self._check_disk_space,
            "memory": self._check_memory,
        }

    def run_all_checks(self) -> dict[str, Any]:
        """Run all health checks and return status."""
        results = {}
        overall_status = HealthCheckStatus.HEALTHY

        for check_name, check_func in self.checks.items():
            try:
                check_result = check_func()
                results[check_name] = check_result

                # Determine overall status
                if check_result["status"] == HealthCheckStatus.UNHEALTHY:
                    overall_status = HealthCheckStatus.UNHEALTHY
                elif (
                    check_result["status"] == HealthCheckStatus.DEGRADED
                    and overall_status == HealthCheckStatus.HEALTHY
                ):
                    overall_status = HealthCheckStatus.DEGRADED

            except Exception as e:
                logger.error(f"Health check '{check_name}' failed: {e}")
                results[check_name] = {
                    "status": HealthCheckStatus.UNHEALTHY,
                    "message": f"Check failed: {str(e)}",
                    "timestamp": timezone.now().isoformat(),
                }
                overall_status = HealthCheckStatus.UNHEALTHY

        return {
            "status": overall_status,
            "timestamp": timezone.now().isoformat(),
            "version": getattr(settings, "VERSION", "1.0.0"),
            "environment": getattr(settings, "ENVIRONMENT", "unknown"),
            "checks": results,
        }

    def _check_database(self) -> dict[str, Any]:
        """Check database connectivity and response time."""
        try:
            start_time = timezone.now()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

            response_time = (timezone.now() - start_time).total_seconds() * 1000

            if response_time > 1000:  # 1 second
                status = HealthCheckStatus.DEGRADED
                message = f"Slow database response: {response_time:.2f}ms"
            else:
                status = HealthCheckStatus.HEALTHY
                message = f"Database responsive: {response_time:.2f}ms"

            return {
                "status": status,
                "message": message,
                "response_time_ms": round(response_time, 2),
                "timestamp": timezone.now().isoformat(),
            }

        except Exception as e:
            return {
                "status": HealthCheckStatus.UNHEALTHY,
                "message": f"Database connection failed: {str(e)}",
                "timestamp": timezone.now().isoformat(),
            }

    def _check_cache(self) -> dict[str, Any]:
        """Check cache connectivity and functionality."""
        try:
            test_key = "health_check_test"
            test_value = "ok"

            start_time = timezone.now()
            cache.set(test_key, test_value, timeout=30)
            cached_value = cache.get(test_key)
            cache.delete(test_key)

            response_time = (timezone.now() - start_time).total_seconds() * 1000

            if cached_value != test_value:
                return {
                    "status": HealthCheckStatus.UNHEALTHY,
                    "message": "Cache read/write test failed",
                    "timestamp": timezone.now().isoformat(),
                }

            if response_time > 500:  # 500ms
                status = HealthCheckStatus.DEGRADED
                message = f"Slow cache response: {response_time:.2f}ms"
            else:
                status = HealthCheckStatus.HEALTHY
                message = f"Cache responsive: {response_time:.2f}ms"

            return {
                "status": status,
                "message": message,
                "response_time_ms": round(response_time, 2),
                "timestamp": timezone.now().isoformat(),
            }

        except Exception as e:
            return {
                "status": HealthCheckStatus.DEGRADED,
                "message": f"Cache connection failed: {str(e)}",
                "timestamp": timezone.now().isoformat(),
            }

    def _check_disk_space(self) -> dict[str, Any]:
        """Check available disk space."""
        try:
            disk_usage = psutil.disk_usage("/")
            used_percent = (disk_usage.used / disk_usage.total) * 100

            max_usage = getattr(settings, "HEALTH_CHECK", {}).get("DISK_USAGE_MAX", 90)

            if used_percent >= max_usage:
                status = HealthCheckStatus.UNHEALTHY
                message = f"Disk usage critical: {used_percent:.1f}%"
            elif used_percent >= max_usage - 10:
                status = HealthCheckStatus.DEGRADED
                message = f"Disk usage high: {used_percent:.1f}%"
            else:
                status = HealthCheckStatus.HEALTHY
                message = f"Disk usage normal: {used_percent:.1f}%"

            return {
                "status": status,
                "message": message,
                "disk_usage_percent": round(used_percent, 1),
                "disk_free_gb": round(disk_usage.free / (1024**3), 2),
                "timestamp": timezone.now().isoformat(),
            }

        except Exception as e:
            return {
                "status": HealthCheckStatus.UNHEALTHY,
                "message": f"Disk space check failed: {str(e)}",
                "timestamp": timezone.now().isoformat(),
            }

    def _check_memory(self) -> dict[str, Any]:
        """Check available memory."""
        try:
            memory = psutil.virtual_memory()
            available_mb = memory.available / (1024**2)

            min_memory = getattr(settings, "HEALTH_CHECK", {}).get("MEMORY_MIN", 100)

            if available_mb < min_memory:
                status = HealthCheckStatus.UNHEALTHY
                message = f"Low memory: {available_mb:.0f}MB available"
            elif available_mb < min_memory * 2:
                status = HealthCheckStatus.DEGRADED
                message = f"Memory usage high: {available_mb:.0f}MB available"
            else:
                status = HealthCheckStatus.HEALTHY
                message = f"Memory usage normal: {available_mb:.0f}MB available"

            return {
                "status": status,
                "message": message,
                "memory_available_mb": round(available_mb, 0),
                "memory_usage_percent": round(memory.percent, 1),
                "timestamp": timezone.now().isoformat(),
            }

        except Exception as e:
            return {
                "status": HealthCheckStatus.UNHEALTHY,
                "message": f"Memory check failed: {str(e)}",
                "timestamp": timezone.now().isoformat(),
            }


# Global health checker instance
health_checker = HealthChecker()


@never_cache
@require_http_methods(["GET", "HEAD"])
def health_check_view(request: Any) -> JsonResponse:
    """Health check endpoint for monitoring systems."""
    health_status = health_checker.run_all_checks()

    # Return appropriate HTTP status code
    if health_status["status"] == HealthCheckStatus.HEALTHY:
        status_code = 200
    elif health_status["status"] == HealthCheckStatus.DEGRADED:
        status_code = 200  # Still operational but with issues
    else:
        status_code = 503  # Service unavailable

    return JsonResponse(health_status, status=status_code)


@never_cache
@require_http_methods(["GET"])
def readiness_check_view(request: Any) -> JsonResponse:
    """Readiness check for Kubernetes/Docker deployments."""
    # Simple readiness check - can the app handle requests?
    try:
        # Check critical components only
        db_check = health_checker._check_database()

        if db_check["status"] == HealthCheckStatus.UNHEALTHY:
            return JsonResponse(
                {"status": "not_ready", "message": "Database not available"}, status=503
            )

        return JsonResponse(
            {"status": "ready", "timestamp": timezone.now().isoformat()}, status=200
        )

    except Exception as e:
        return JsonResponse({"status": "not_ready", "error": str(e)}, status=503)


@never_cache
@require_http_methods(["GET"])
def liveness_check_view(request: Any) -> JsonResponse:
    """Liveness check for Kubernetes/Docker deployments."""
    # Simple liveness check - is the app running?
    return JsonResponse(
        {
            "status": "alive",
            "timestamp": timezone.now().isoformat(),
            "version": getattr(settings, "VERSION", "1.0.0"),
        },
        status=200,
    )
