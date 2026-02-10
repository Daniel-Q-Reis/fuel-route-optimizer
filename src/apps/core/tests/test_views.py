"""
Tests for core health check views.

Comprehensive test suite for the senior-level health check implementation.
"""

import json
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import Client, TestCase

from src.apps.core.health import HealthChecker


class HealthCheckViewTests(TestCase):
    """Test suite for health check endpoints."""

    def setUp(self):
        """Set up test client and clear cache."""
        self.client = Client()
        cache.clear()

    def test_health_check_success(self):
        """Test health check returns 200 when all components are healthy."""
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        data = json.loads(response.content)
        self.assertEqual(data["status"], "healthy")
        self.assertIn("timestamp", data)
        self.assertIn("version", data)
        self.assertIn("environment", data)
        self.assertIn("checks", data)

        # Check components structure
        checks = data["checks"]
        self.assertIn("database", checks)
        self.assertIn("cache", checks)
        self.assertIn("disk_space", checks)
        self.assertIn("memory", checks)

        # Database should be healthy in tests
        self.assertEqual(checks["database"]["status"], "healthy")

    def test_health_check_head_request(self):
        """Test health check supports HEAD requests for load balancers."""
        response = self.client.head("/health/")
        self.assertEqual(response.status_code, 200)

    @patch("src.apps.core.health.connection")
    def test_health_check_database_failure(self, mock_connection):
        """Test health check returns 503 when database is down."""
        # Mock database connection failure
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Database connection failed")
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 503)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "unhealthy")
        self.assertEqual(data["checks"]["database"]["status"], "unhealthy")

    @patch("src.apps.core.health.cache")
    def test_health_check_cache_warning(self, mock_cache):
        """Test health check handles cache failures gracefully."""
        # Mock cache failure
        mock_cache.set.side_effect = Exception("Redis connection failed")

        response = self.client.get("/health/")

        # Should still return 200 as cache is not critical
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["checks"]["cache"]["status"], "degraded")

    def test_health_check_caching(self):
        """Test health check endpoint is never cached."""
        response1 = self.client.get("/health/")
        response2 = self.client.get("/health/")

        # Both requests should return 200
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)

        # Check cache control headers
        self.assertIn("Cache-Control", response1)
        self.assertIn("no-cache", response1["Cache-Control"])

    def test_health_check_response_headers(self):
        """Test health check includes proper response headers."""
        response = self.client.get("/health/")

        # Should include cache control headers to prevent caching
        self.assertIn("Cache-Control", response)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_health_check_invalid_method(self):
        """Test health check only accepts GET and HEAD methods."""
        # POST should not be allowed
        response = self.client.post("/health/")
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

        # PUT should not be allowed
        response = self.client.put("/health/")
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_readiness_check_success(self):
        """Test readiness check returns 200 when ready."""
        response = self.client.get("/health/ready/")

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "ready")
        self.assertIn("timestamp", data)

    @patch("src.apps.core.health.connection")
    def test_readiness_check_failure(self, mock_connection):
        """Test readiness check returns 503 when not ready."""
        # Mock database connection failure
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Database connection failed")
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        response = self.client.get("/health/ready/")

        self.assertEqual(response.status_code, 503)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "not_ready")

    def test_liveness_check(self):
        """Test liveness check always returns 200."""
        response = self.client.get("/health/live/")

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "alive")
        self.assertIn("timestamp", data)
        self.assertIn("version", data)

    def test_kubernetes_aliases(self):
        """Test Kubernetes-style health check aliases."""
        # Test /healthz
        response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 200)

        # Test /readyz
        response = self.client.get("/readyz/")
        self.assertEqual(response.status_code, 200)

        # Test /livez
        response = self.client.get("/livez/")
        self.assertEqual(response.status_code, 200)


class HealthCheckerUnitTests(TestCase):
    """Unit tests for the HealthChecker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.health_checker = HealthChecker()

    def test_health_checker_initialization(self):
        """Test HealthChecker initializes with all checks."""
        expected_checks = ["database", "cache", "disk_space", "memory"]

        for check in expected_checks:
            self.assertIn(check, self.health_checker.checks)

    @patch("src.apps.core.health.connection")
    def test_database_check_success(self, mock_connection):
        """Test database check returns healthy status."""
        # Mock successful database connection
        mock_cursor = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        result = self.health_checker._check_database()

        self.assertEqual(result["status"], "healthy")
        self.assertIn("response_time_ms", result)
        self.assertIn("timestamp", result)

    @patch("src.apps.core.health.connection")
    def test_database_check_failure(self, mock_connection):
        """Test database check returns unhealthy status on failure."""
        # Mock database connection failure
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Connection failed")
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        result = self.health_checker._check_database()

        self.assertEqual(result["status"], "unhealthy")
        self.assertIn("message", result)
        self.assertIn("Connection failed", result["message"])

    @patch("src.apps.core.health.cache")
    def test_cache_check_success(self, mock_cache):
        """Test cache check returns healthy status."""
        # Mock successful cache operations
        mock_cache.get.return_value = "ok"

        result = self.health_checker._check_cache()

        self.assertEqual(result["status"], "healthy")
        self.assertIn("response_time_ms", result)

    @patch("src.apps.core.health.cache")
    def test_cache_check_failure(self, mock_cache):
        """Test cache check returns unhealthy status on failure."""
        # Mock cache failure
        mock_cache.set.side_effect = Exception("Redis connection failed")
        result = self.health_checker._check_cache()

        self.assertEqual(result["status"], "degraded")
        self.assertIn("Redis connection failed", result["message"])

    @patch("src.apps.core.health.psutil")
    def test_disk_check_healthy(self, mock_psutil):
        """Test disk space check returns healthy status."""
        # Mock disk usage at 50%
        mock_disk = MagicMock()
        mock_disk.total = 1000000000
        mock_disk.used = 500000000
        mock_disk.free = 500000000
        mock_psutil.disk_usage.return_value = mock_disk

        result = self.health_checker._check_disk_space()

        self.assertEqual(result["status"], "healthy")
        self.assertIn("disk_usage_percent", result)
        self.assertEqual(result["disk_usage_percent"], 50.0)

    @patch("src.apps.core.health.psutil")
    def test_disk_check_unhealthy(self, mock_psutil):
        """Test disk space check returns unhealthy status when full."""
        # Mock disk usage at 95%
        mock_disk = MagicMock()
        mock_disk.total = 1000000000
        mock_disk.used = 950000000
        mock_disk.free = 50000000
        mock_psutil.disk_usage.return_value = mock_disk

        result = self.health_checker._check_disk_space()

        self.assertEqual(result["status"], "unhealthy")
        self.assertIn("Disk usage critical", result["message"])

    def test_run_all_checks_integration(self):
        """Test running all health checks together."""
        result = self.health_checker.run_all_checks()

        self.assertIn("status", result)
        self.assertIn("timestamp", result)
        self.assertIn("version", result)
        self.assertIn("environment", result)
        self.assertIn("checks", result)

        # Should have all expected checks
        expected_checks = ["database", "cache", "disk_space", "memory"]
        for check in expected_checks:
            self.assertIn(check, result["checks"])
