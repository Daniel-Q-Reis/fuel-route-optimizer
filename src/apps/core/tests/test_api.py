import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from faker import Faker
from rest_framework.test import APIClient

from src.apps.core.models import Post
from src.apps.core.services import create_post

User = get_user_model()
fake = Faker()


@pytest.fixture
def api_client():
    """Pytest fixture for providing a DRF API client."""
    return APIClient()


@pytest.fixture
def user_data():
    """Pytest fixture for generating fake user data."""
    password = fake.password()
    user = User.objects.create_user(
        username=fake.user_name(),
        email=fake.email(),
        password=password,
    )
    return {"user": user, "password": password}


@pytest.fixture
def authenticated_client(api_client, user_data):
    """Pytest fixture for providing an authenticated API client."""
    api_client.force_authenticate(user=user_data["user"])
    return api_client


class CoreAPITestCase(TestCase):
    def test_api_docs_is_available(self):
        """Asserts that the API documentation (Swagger UI) is available and returns a 200 OK status."""
        url = reverse("swagger-ui")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


@pytest.mark.django_db
def test_health_check_api_view_status_code(api_client):
    """
    Tests that the HealthCheckAPIView returns a 200 OK status.
    """
    url = reverse("core:api-health-check")
    response = api_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_health_check_api_view_response_data(api_client):
    """
    Tests the response structure and content of the HealthCheckAPIView.
    """
    url = reverse("core:api-health-check")
    response = api_client.get(url)
    data = response.json()

    assert "status" in data
    assert "version" in data
    assert "timestamp" in data
    assert data["status"] == "ok"


@pytest.mark.django_db
class TestPostAPI:
    """Tests for the Post API endpoints."""

    def test_list_posts(self, api_client, user_data):
        """Asserts that the API can list posts."""
        create_post(
            author=user_data["user"], title=fake.sentence(), content=fake.paragraph()
        )
        create_post(
            author=user_data["user"], title=fake.sentence(), content=fake.paragraph()
        )

        response = api_client.get("/api/posts/")

        assert response.status_code == 200
        assert len(response.data["results"]) == 2

    def test_create_post(self, authenticated_client):
        """Asserts that an authenticated user can create a post."""
        post_data = {"title": fake.sentence(), "content": fake.paragraph()}

        response = authenticated_client.post(
            "/api/posts/", data=post_data, format="json"
        )

        assert response.status_code == 201
        assert Post.objects.count() == 1
        assert Post.objects.first().title == post_data["title"]

    def test_unauthenticated_create_post(self, api_client):
        """Asserts that an unauthenticated user cannot create a post."""
        post_data = {"title": fake.sentence(), "content": fake.paragraph()}

        response = api_client.post("/api/posts/", data=post_data)

        assert response.status_code == 403

    def test_retrieve_post(self, api_client, user_data):
        """Asserts that a post can be retrieved by its slug."""
        post = create_post(
            author=user_data["user"], title=fake.sentence(), content=fake.paragraph()
        )

        response = api_client.get(f"/api/posts/{post.slug}/")

        assert response.status_code == 200
        assert response.data["title"] == post.title

    def test_update_post(self, authenticated_client, user_data):
        """Asserts that an authenticated user can update a post."""
        post = create_post(
            author=user_data["user"], title=fake.sentence(), content=fake.paragraph()
        )
        update_data = {"title": "Updated Title", "content": "Updated content."}

        response = authenticated_client.put(
            f"/api/posts/{post.slug}/", data=update_data, format="json"
        )
        post.refresh_from_db()

        assert response.status_code == 200
        assert post.title == update_data["title"]

    def test_delete_post(self, authenticated_client, user_data):
        """Asserts that an authenticated user can soft-delete a post."""
        post = create_post(
            author=user_data["user"], title=fake.sentence(), content=fake.paragraph()
        )

        response = authenticated_client.delete(f"/api/posts/{post.slug}/")
        post.refresh_from_db()

        assert response.status_code == 204
        assert post.is_active is False

    def test_update_post_of_another_user(self, api_client, user_data):
        """Asserts that a user cannot update a post of another user."""
        # Create a post with the first user
        post = create_post(
            author=user_data["user"], title=fake.sentence(), content=fake.paragraph()
        )

        # Create a second user and authenticate
        new_user_data = {
            "user": User.objects.create_user(
                username=fake.user_name(), password=fake.password()
            ),
            "password": fake.password(),
        }
        api_client.force_authenticate(user=new_user_data["user"])

        update_data = {"title": "Updated Title", "content": "Updated content."}

        response = api_client.put(
            f"/api/posts/{post.slug}/", data=update_data, format="json"
        )

        assert response.status_code == 403

    def test_delete_post_of_another_user(self, api_client, user_data):
        """Asserts that a user cannot delete a post of another user."""
        # Create a post with the first user
        post = create_post(
            author=user_data["user"], title=fake.sentence(), content=fake.paragraph()
        )

        # Create a second user and authenticate
        new_user_data = {
            "user": User.objects.create_user(
                username=fake.user_name(), password=fake.password()
            ),
            "password": fake.password(),
        }
        api_client.force_authenticate(user=new_user_data["user"])

        response = api_client.delete(f"/api/posts/{post.slug}/")

        assert response.status_code == 403
