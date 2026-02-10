"""
Core app URL configuration.

Includes health checks and other core functionality.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .health import (
    health_check_view,
    liveness_check_view,
    readiness_check_view,
)
from .views import HealthCheckAPIView, PostViewSet

app_name = "core"

# API Router
router = DefaultRouter()
router.register(r"posts", PostViewSet, basename="post")

urlpatterns = [
    # Health check endpoints for monitoring
    path("health/", health_check_view, name="health-check"),
    path("health/ready/", readiness_check_view, name="readiness-check"),
    path("health/live/", liveness_check_view, name="liveness-check"),
    # Alias for Kubernetes/Docker health checks
    path("healthz/", health_check_view, name="healthz"),
    path("readyz/", readiness_check_view, name="readyz"),
    path("livez/", liveness_check_view, name="livez"),
    # API endpoint for health check
    path("api/health/", HealthCheckAPIView.as_view(), name="api-health-check"),
    # API endpoints from the router
    path("api/", include(router.urls)),
]
