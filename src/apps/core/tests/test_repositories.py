"""
Unit tests for the core repositories.
"""

import pytest
from django.contrib.auth import get_user_model
from faker import Faker

from src.apps.core import repositories
from src.apps.core.models import Post

User = get_user_model()
fake = Faker()


@pytest.mark.django_db
class TestPostRepository:
    """
    Tests for the Post repository functions.
    """

    def test_create_post_repository(self):
        """
        Tests that the create_post repository function creates a Post in the database.
        """
        # Arrange
        author = User.objects.create_user(
            username=fake.user_name(), password=fake.password()
        )
        title = fake.sentence()
        content = fake.paragraph()

        # Act
        post = repositories.create_post(author=author, title=title, content=content)

        # Assert
        assert Post.objects.count() == 1
        assert isinstance(post, Post)
        assert post.title == title
        assert post.author == author

    def test_get_active_posts_repository(self):
        """
        Tests that the get_active_posts repository function returns only active posts.
        """
        # Arrange
        author = User.objects.create_user(
            username=fake.user_name(), password=fake.password()
        )
        # Create active posts
        repositories.create_post(
            author=author, title=fake.sentence(), content=fake.paragraph()
        )
        repositories.create_post(
            author=author, title=fake.sentence(), content=fake.paragraph()
        )

        # Create an inactive post
        inactive_post = repositories.create_post(
            author=author, title=fake.sentence(), content=fake.paragraph()
        )
        inactive_post.soft_delete()

        # Act
        active_posts = repositories.get_active_posts()

        # Assert
        assert active_posts.count() == 2
        for post in active_posts:
            assert post.is_active is True
