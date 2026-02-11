import json
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse

from src.apps.core.health import HealthChecker, HealthCheckStatus


class HealthCheckTest(TestCase):
    """Deep tests for health check functionality and views."""

    def setUp(self) -> None:
        self.checker = HealthChecker()
        self.health_url = reverse("core:health-check")
        self.ready_url = reverse("core:readiness-check")
        self.live_url = reverse("core:liveness-check")

    @patch("src.apps.core.health.psutil")
    @patch("src.apps.core.health.cache")
    @patch("src.apps.core.health.connection")
    def test_run_all_checks_healthy(
        self, mock_conn: MagicMock, mock_cache: MagicMock, mock_psutil: MagicMock
    ) -> None:
        """Test healthy status when all components are fine."""
        mock_psutil.disk_usage.return_value.used = 10
        mock_psutil.disk_usage.return_value.total = 100
        mock_psutil.disk_usage.return_value.free = 90
        mock_psutil.virtual_memory.return_value.available = 1024 * 1024 * 500  # 500MB
        mock_psutil.virtual_memory.return_value.percent = 50
        mock_cache.get.return_value = "ok"

        results = self.checker.run_all_checks()
        self.assertEqual(results["status"], HealthCheckStatus.HEALTHY)
        self.assertEqual(
            results["checks"]["database"]["status"], HealthCheckStatus.HEALTHY
        )

    @patch("src.apps.core.health.cache")
    def test_cache_mismatch(self, mock_cache: MagicMock) -> None:
        """Cover line 123: Cache read/write test failure."""
        mock_cache.get.return_value = "wrong_value"
        result = self.checker._check_cache()
        self.assertEqual(result["status"], HealthCheckStatus.UNHEALTHY)
        self.assertEqual(result["message"], "Cache read/write test failed")

    @patch("src.apps.core.health.psutil.disk_usage")
    def test_disk_usage_high_degraded(self, mock_disk: MagicMock) -> None:
        """Cover lines 162-163: Disk usage high (degraded)."""
        mock_disk.return_value.used = 85
        mock_disk.return_value.total = 100
        mock_disk.return_value.free = 15
        result = self.checker._check_disk_space()
        self.assertEqual(result["status"], HealthCheckStatus.DEGRADED)
        self.assertIn("Disk usage high", result["message"])

    @patch("src.apps.core.health.psutil.disk_usage")
    def test_disk_usage_exception(self, mock_disk: MagicMock) -> None:
        """Cover lines 176-177: Disk check exception."""
        mock_disk.side_effect = Exception("Disk error")
        result = self.checker._check_disk_space()
        self.assertEqual(result["status"], HealthCheckStatus.UNHEALTHY)
        self.assertIn("Disk space check failed", result["message"])

    @patch("src.apps.core.health.psutil.virtual_memory")
    def test_memory_usage_unhealthy_and_degraded(self, mock_mem: MagicMock) -> None:
        """Cover lines 192-193 and 195-196: Low memory and High usage."""
        mock_mem.return_value.available = 50 * 1024 * 1024  # 50MB
        mock_mem.return_value.percent = 95
        result = self.checker._check_memory()
        self.assertEqual(result["status"], HealthCheckStatus.UNHEALTHY)

        mock_mem.return_value.available = 150 * 1024 * 1024  # 150MB
        result = self.checker._check_memory()
        self.assertEqual(result["status"], HealthCheckStatus.DEGRADED)

    @patch("src.apps.core.health.psutil.virtual_memory")
    def test_memory_exception(self, mock_mem: MagicMock) -> None:
        """Cover lines 209-210: Memory check exception."""
        mock_mem.side_effect = Exception("Memory error")
        result = self.checker._check_memory()
        self.assertEqual(result["status"], HealthCheckStatus.UNHEALTHY)
        self.assertIn("Memory check failed", result["message"])

    def test_run_all_checks_exception(self) -> None:
        """Cover lines 61-68: Exception during one of the checks."""
        self.checker.checks["database"] = MagicMock(
            side_effect=Exception("Internal check error")
        )
        results = self.checker.run_all_checks()
        self.assertEqual(results["status"], HealthCheckStatus.UNHEALTHY)
        self.assertEqual(
            results["checks"]["database"]["status"], HealthCheckStatus.UNHEALTHY
        )
        self.assertIn("Check failed", results["checks"]["database"]["message"])

    @patch("src.apps.core.health.health_checker")
    def test_readiness_check_exception(self, mock_health_checker: MagicMock) -> None:
        """Cover lines 256-257: Readiness check exception."""
        mock_health_checker._check_database.side_effect = Exception("Readiness error")
        response = self.client.get(self.ready_url)
        self.assertEqual(response.status_code, 503)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "not_ready")

    def test_liveness_check(self) -> None:
        """Test liveness endpoint."""
        response = self.client.get(self.live_url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "alive")

    @patch("src.apps.core.health.health_checker.run_all_checks")
    def test_health_view_unhealthy(self, mock_run: MagicMock) -> None:
        """Test health view with unhealthy status."""
        mock_run.return_value = {"status": HealthCheckStatus.UNHEALTHY, "checks": {}}
        response = self.client.get(self.health_url)
        self.assertEqual(response.status_code, 503)

    @patch("src.apps.core.health.health_checker.run_all_checks")
    def test_health_view_degraded(self, mock_run: MagicMock) -> None:
        """Test health view with degraded status."""
        mock_run.return_value = {"status": HealthCheckStatus.DEGRADED, "checks": {}}
        response = self.client.get(self.health_url)
        self.assertEqual(response.status_code, 200)
