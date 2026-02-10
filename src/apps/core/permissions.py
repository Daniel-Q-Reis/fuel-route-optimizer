"""
Custom permissions for the core app.
"""

from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it,
    and require authentication for write operations.
    """

    def has_permission(self, request, view):
        # Allow read-only access for any request (authenticated or not).
        if request.method in permissions.SAFE_METHODS:
            return True

        # For write operations, require the user to be authenticated.
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the author of the post.
        return obj.author == request.user
