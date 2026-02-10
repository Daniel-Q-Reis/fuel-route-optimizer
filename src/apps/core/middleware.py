"""Custom middleware for the application."""

import logging
import time
import uuid

from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(MiddlewareMixin):
    """Middleware to log request/response information for monitoring.

    Logs:
    - Request method, path, user agent
    - Response status code and duration
    - Request ID for tracing
    - User information if authenticated
    """

    def process_request(self, request):
        """Add request metadata and start timer."""
        request.start_time = time.time()
        request.request_id = str(uuid.uuid4())[:8]

        # Add request ID to response headers for debugging
        request._request_id = request.request_id

        return None

    def process_response(self, request, response):
        """Log request completion with timing and response info."""
        if not hasattr(request, "start_time"):
            return response

        duration = time.time() - request.start_time

        # Skip logging for static files and health checks
        skip_paths = ["/static/", "/media/", "/favicon.ico"]
        if any(request.path.startswith(path) for path in skip_paths):
            return response

        # Prepare log data
        log_data = {
            "request_id": getattr(request, "request_id", "unknown"),
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:100],
            "ip_address": self._get_client_ip(request),
            "timestamp": timezone.now().isoformat(),
        }

        # Add user info if authenticated
        if hasattr(request, "user") and request.user.is_authenticated:
            log_data["user_id"] = request.user.id
            log_data["username"] = request.user.username

        # Add query params for GET requests (be careful with sensitive data)
        if request.method == "GET" and request.GET:
            # Only log safe query parameters
            safe_params = {
                k: v
                for k, v in request.GET.items()
                if k not in ["password", "token", "secret", "key"]
            }
            if safe_params:
                log_data["query_params"] = safe_params

        # Log at appropriate level based on status code
        if response.status_code >= 500:
            logger.error(f"Request completed: {log_data}")
        elif response.status_code >= 400:
            logger.warning(f"Request completed: {log_data}")
        else:
            logger.info(f"Request completed: {log_data}")

        # Add request ID to response headers for debugging
        response["X-Request-ID"] = request.request_id

        return response

    def _get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
            return ip.strip()
        return request.META.get("REMOTE_ADDR", "unknown")


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to all responses.

    This middleware adds various security headers to protect against
    common web vulnerabilities.
    """

    def process_response(self, request, response):
        """Add security headers to response."""
        # Prevent page from being displayed in a frame/iframe
        response["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response["X-Content-Type-Options"] = "nosniff"

        # Enable XSS filtering
        response["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Feature policy (basic)
        response["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response


class HealthCheckMiddleware(MiddlewareMixin):
    """Lightweight middleware for health check endpoints.

    Bypasses expensive middleware for health check requests
    to ensure fast response times for load balancers.
    """

    def process_request(self, request):
        """Skip processing for health check endpoints."""
        if request.path in ["/health/", "/health", "/ping"]:
            # Mark request as health check to skip other middleware
            request._is_health_check = True
        return None
