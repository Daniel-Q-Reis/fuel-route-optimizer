"""
Core app tests package.

This package contains all tests for the core application.
"""

# Import test classes to make them discoverable
from .test_api import *  # noqa: F403, F401
from .test_models import *  # noqa: F403, F401
from .test_views import *  # noqa: F403, F401

__all__ = [
    # Test classes will be automatically discovered
]
