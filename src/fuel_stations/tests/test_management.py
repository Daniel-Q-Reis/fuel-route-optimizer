"""Tests for management commands with high coverage."""

from unittest.mock import patch, MagicMock 
from django.core.management import call_command
from django.test import TestCase

class ManagementCommandTest(TestCase):
    """Test suite for custom management commands."""

    @patch("fuel_stations.management.commands.benchmark_baseline.requests.post")
    def test_benchmark_baseline_success(self, mock_post):
        """Test the benchmark_baseline command with successful responses (Happy Path)."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.05
        mock_post.return_value = mock_response

        # Execute command
        call_command("benchmark_baseline")

        # Verify calls:
        # 1 warmup + (3 routes * 3 iterations) = 10 calls
        self.assertEqual(mock_post.call_count, 10)

    @patch("fuel_stations.management.commands.benchmark_baseline.requests.post")
    def test_benchmark_baseline_api_error(self, mock_post):
        """Test the benchmark_baseline command handling API errors."""
        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        # Execute command
        call_command("benchmark_baseline")
        
        # Should still run through all iterations even if they fail
        self.assertEqual(mock_post.call_count, 10)

    @patch("fuel_stations.management.commands.benchmark_cached.cache")
    @patch("fuel_stations.management.commands.benchmark_cached.requests.post")
    def test_benchmark_cached_success(self, mock_post, mock_cache):
        """Test the benchmark_cached command with successful responses."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.05
        mock_post.return_value = mock_response

        # Execute
        call_command("benchmark_cached")

        # Verify calls: 
        # Miss loop (3) + Hit loop (10) = 13 calls
        self.assertEqual(mock_post.call_count, 13)
        # Check cache was cleared (initial + inside miss loop)
        self.assertTrue(mock_cache.clear.called)

    @patch("fuel_stations.management.commands.benchmark_cached.cache")
    @patch("fuel_stations.management.commands.benchmark_cached.requests.post")
    def test_benchmark_cached_api_error(self, mock_post, mock_cache):
        """Test the benchmark_cached command handling API errors."""
        mock_response = MagicMock()
        mock_response.status_code = 500  # Error
        mock_post.return_value = mock_response

        # Execute
        call_command("benchmark_cached")

        # Should still attempt all requests
        self.assertEqual(mock_post.call_count, 13)
        
    @patch("fuel_stations.management.commands.benchmark_baseline.requests.post")
    def test_benchmark_baseline_mixed_response(self, mock_post):
        """Test mixed success/failure to ensure list handling works."""
        # Side effect: First succeed, then fail
        success = MagicMock(status_code=200)
        success.elapsed.total_seconds.return_value = 0.1
        failure = MagicMock(status_code=400)
        
        # 10 calls total. Let's mix them.
        mock_post.side_effect = [success] * 5 + [failure] * 5
        
        call_command("benchmark_baseline")
        self.assertEqual(mock_post.call_count, 10)

