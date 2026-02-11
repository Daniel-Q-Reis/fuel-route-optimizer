"""
Custom permissions for the core app.
"""

from typing import Any

from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):  # type: ignore[misc]
    """
    Custom permission to only allow owners of an object to edit it,
    and require authentication for write operations.
    """

    def has_permission(self, request: Any, view: Any) -> bool:
        # Allow read-only access for any request (authenticated or not).
        if request.method in permissions.SAFE_METHODS:
            return True

        # For write operations, require the user to be authenticated.
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request: Any, view: Any, obj: Any) -> bool:
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the author of the post.
        return bool(obj.author == request.user)
