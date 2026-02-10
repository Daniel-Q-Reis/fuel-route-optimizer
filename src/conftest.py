"""
Pytest configuration and global fixtures.

Defines common fixtures and settings for the entire test suite.
"""

import os

import django
from django.conf import settings

# Configure Django settings before any Django imports
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.config.settings.test")
    django.setup()

# Now safe to import Django and DRF components
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="testpass123"
    )


@pytest.fixture
def admin_user():
    """Create an admin test user."""
    return User.objects.create_superuser(
        username="admin", email="admin@example.com", password="adminpass123"
    )


@pytest.fixture
def client():
    """Django test client."""
    return Client()


@pytest.fixture
def api_client():
    """DRF API test client."""
    return APIClient()


@pytest.fixture
def authenticated_client(client, user):
    """Authenticated Django test client."""
    client.force_login(user)
    return client


@pytest.fixture
def authenticated_api_client(api_client, user):
    """Authenticated DRF API test client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_client(client, admin_user):
    """Admin authenticated Django test client."""
    client.force_login(admin_user)
    return client


@pytest.fixture
def admin_api_client(api_client, admin_user):
    """Admin authenticated DRF API test client."""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Enable database access for all tests by default."""
    pass


# Pytest markers for organizing tests
pytestmark = [
    pytest.mark.django_db,
]
