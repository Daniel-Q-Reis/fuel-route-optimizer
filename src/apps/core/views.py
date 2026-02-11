"""Core views for the application."""

import logging
from datetime import datetime
from typing import Any

from django.conf import settings
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import repositories, services
from .permissions import IsOwnerOrReadOnly
from .serializers import HealthCheckSerializer, PostSerializer

logger = logging.getLogger(__name__)


class HealthCheckAPIView(APIView):  # type: ignore[misc]
    """
    API view for health check.

    Provides a structured health check response using DRF Serializer.
    This is more aligned with standard API practices.
    """

    permission_classes = [AllowAny]
    serializer_class = HealthCheckSerializer

    def get(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        """
        Return the health status of the application.
        """
        # Simplified check for the API view, more detailed one is in the function-based view
        data = {
            "status": "ok",
            "version": getattr(settings, "VERSION", "1.0.0"),
            "timestamp": datetime.utcnow(),
        }
        serializer = self.serializer_class(instance=data)
        return Response(serializer.data)


@extend_schema(tags=["Posts"])
class PostViewSet(viewsets.ModelViewSet):  # type: ignore[misc]
    """
    API endpoint that allows posts to be viewed or edited.

    Provides a full CRUD interface for the Post model.
    - `list`: Returns a list of all active posts.
    - `create`: Creates a new post. Requires authentication.
    - `retrieve`: Retrieves a single post by its slug.
    - `update`: Updates a post. Requires authentication.
    - `partial_update`: Partially updates a post. Requires authentication.
    - `destroy`: Soft-deletes a post. Requires authentication.
    """

    queryset = repositories.get_active_posts()
    serializer_class = PostSerializer
    permission_classes = [IsOwnerOrReadOnly]
    lookup_field = "slug"

    @extend_schema(
        summary="List all active posts",
        description="Returns a paginated list of all posts that are marked as active.",
    )
    def list(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new post",
        description="Creates a new post. The author will be set to the currently authenticated user.",
        examples=[
            OpenApiExample(
                "Create a new post",
                value={
                    "title": "My New Post Title",
                    "content": "This is the content of my new post.",
                },
                request_only=True,
            ),
        ],
    )
    def create(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a post",
        description="Retrieves a single post by its unique slug.",
    )
    def retrieve(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a post",
        description="Updates a post. Only the author of the post can perform this action.",
        examples=[
            OpenApiExample(
                "Update a post",
                value={
                    "title": "My Updated Post Title",
                    "content": "This is the updated content of my post.",
                },
                request_only=True,
            ),
        ],
    )
    def update(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a post",
        description="Partially updates a post. Only the author of the post can perform this action.",
    )
    def partial_update(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a post",
        description="Soft-deletes a post by marking it as inactive. Only the author of the post can perform this action.",
    )
    def destroy(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer: Any) -> None:
        """
        Overrides the default create method to use the `create_post` service.
        This ensures that the author is correctly set to the request user.
        """
        services.create_post(author=self.request.user, **serializer.validated_data)

    def perform_destroy(self, instance: Any) -> None:
        """
        Overrides the default destroy method to perform a soft delete.
        """
        instance.soft_delete()
