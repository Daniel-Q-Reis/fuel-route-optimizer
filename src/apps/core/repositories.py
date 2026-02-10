"""
Core Repositories for the application.

This file contains the data access logic for the core app.
Repositories are used to abstract the data access layer from the services,
following the Repository Pattern. This helps in:
- Decoupling business logic from data access details (e.g., ORM).
- Improving testability by allowing repositories to be mocked.
- Centralizing query logic for reuse.
"""

from typing import TYPE_CHECKING

from django.db.models.query import QuerySet

from .models import Post

if TYPE_CHECKING:
    from django.contrib.auth.models import User


def create_post(*, author: "User", title: str, content: str) -> Post:
    """
    Creates and returns a new Post instance in the database.

    Args:
        author: The user creating the post.
        title: The title of the post.
        content: The content of the post.

    Returns:
        The newly created Post instance.
    """
    return Post.objects.create(author=author, title=title, content=content)


def get_active_posts() -> QuerySet[Post]:
    """
    Returns a queryset of all active posts.
    """
    return Post.objects.active()
