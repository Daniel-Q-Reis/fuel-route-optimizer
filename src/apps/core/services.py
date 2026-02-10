"""
Core Services for the application.

This file contains the business logic services for the core app.
Services are used to abstract the business logic from the views and
to orchestrate the application's operations.

Following the Service Layer pattern helps in:
- Decoupling business logic from the web layer (views).
- Improving testability by isolating logic.
- Reusing logic across different parts of the application (e.g., views, management commands).
"""

import logging
from typing import TYPE_CHECKING

from . import repositories
from .models import Post

if TYPE_CHECKING:
    from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


def create_post(*, author: "User", title: str, content: str) -> Post:
    """
    Creates a new post.

    This function encapsulates the business logic for creating a post,
    such as setting the author and handling any other related logic
    (e.g., sending notifications, etc., which can be added later).

    Args:
        author: The user creating the post.
        title: The title of the post.
        content: The content of the post.

    Returns:
        The newly created Post instance.
    """
    post = repositories.create_post(author=author, title=title, content=content)
    logger.info(
        "Post created successfully.",
        extra={"post_id": post.id, "author_id": author.id},
    )
    # In a real application, you might have more logic here:
    # - Send a notification
    # - Create an audit log entry
    # - Trigger a background task
    return post
