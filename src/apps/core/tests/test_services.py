"""
Unit tests for the core services.
"""

import pytest
from django.contrib.auth import get_user_model
from faker import Faker

from src.apps.core import services
from src.apps.core.models import Post

User = get_user_model()
fake = Faker()


@pytest.mark.django_db
def test_create_post_service(mocker):
    """
    Tests that the create_post service correctly calls the repository and returns a Post.
    """
    # Arrange
    author = User.objects.create_user(
        username=fake.user_name(), password=fake.password()
    )
    title = fake.sentence()
    content = fake.paragraph()

    # Mock the repository function
    mock_repo_create_post = mocker.patch(
        "src.apps.core.repositories.create_post",
        return_value=Post(id=1, author=author, title=title, content=content),
    )

    # Act
    post = services.create_post(author=author, title=title, content=content)

    # Assert
    mock_repo_create_post.assert_called_once_with(
        author=author, title=title, content=content
    )
    assert isinstance(post, Post)
    assert post.title == title
    assert post.author == author
