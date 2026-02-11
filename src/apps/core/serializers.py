"""
Core serializers for the application.
"""

from rest_framework import serializers

from .models import Post


class HealthCheckSerializer(serializers.Serializer):  # type: ignore[misc]
    """
    Serializer for the health check endpoint.
    """

    status = serializers.CharField(read_only=True)
    version = serializers.CharField(read_only=True)
    timestamp = serializers.DateTimeField(read_only=True)


class PostSerializer(serializers.ModelSerializer):  # type: ignore[misc]
    """
    Serializer for the Post model.

    Handles validation and serialization for Post objects, making them
    renderable as JSON for the API.
    """

    author = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "title",
            "slug",
            "content",
            "author",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["slug", "author", "is_active"]
