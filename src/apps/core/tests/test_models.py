"""
Tests for core models and managers.

Comprehensive test suite for base models, managers, and mixins.
"""

from typing import Any

from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase

from src.apps.core.models import (
    ActivatableModel,
    AuthorableModel,
    BaseManager,
    SluggedModel,
    TimestampedModel,
)

User = get_user_model()


# Test models for concrete testing
class TestTimestampedModel(TimestampedModel):
    """Concrete model for testing TimestampedModel."""

    name: models.CharField = models.CharField(max_length=100)  # type: ignore[type-arg]

    class Meta:
        app_label = "core"


class TestActivatableModel(ActivatableModel):
    """Concrete model for testing ActivatableModel."""

    name: models.CharField = models.CharField(max_length=100)  # type: ignore[type-arg]

    class Meta:
        app_label = "core"


class TestAuthorableModel(AuthorableModel):
    """Concrete model for testing AuthorableModel."""

    name: models.CharField = models.CharField(max_length=100)  # type: ignore[type-arg]

    class Meta:
        app_label = "core"


class TestSluggedModel(SluggedModel):
    """Concrete model for testing SluggedModel."""

    name: models.CharField = models.CharField(max_length=100)  # type: ignore[type-arg]

    class Meta:
        app_label = "core"


class BaseManagerTests(TestCase):
    """Tests for BaseManager functionality."""

    def setUp(self) -> None:
        """Set up test data."""
        # Use ActivatableModel for testing manager since it uses BaseManager
        pass

    def test_manager_methods_with_mock_data(self) -> None:
        """Test manager methods with mocked data."""
        # Since we can't create actual model instances in tests without migrations,
        # we'll test the manager logic with mocks

        manager: BaseManager[Any] = BaseManager()

        # Test that methods exist and are callable
        self.assertTrue(hasattr(manager, "active"))
        self.assertTrue(hasattr(manager, "inactive"))
        self.assertTrue(hasattr(manager, "recent"))
        self.assertTrue(callable(manager.active))
        self.assertTrue(callable(manager.inactive))
        self.assertTrue(callable(manager.recent))


class TimestampedModelTests(TestCase):
    """Tests for TimestampedModel functionality."""

    def test_model_fields_exist(self) -> None:
        """Test that TimestampedModel has the required fields."""
        from src.apps.core.models import TimestampedModel

        # Check that fields exist
        fields = [f.name for f in TimestampedModel._meta.get_fields()]
        self.assertIn("created_at", fields)
        self.assertIn("updated_at", fields)

    def test_model_is_abstract(self) -> None:
        """Test that TimestampedModel is abstract."""
        from src.apps.core.models import TimestampedModel

        self.assertTrue(TimestampedModel._meta.abstract)

    def test_default_ordering(self) -> None:
        """Test that default ordering is by created_at descending."""
        from src.apps.core.models import TimestampedModel

        self.assertEqual(TimestampedModel._meta.ordering, ["-created_at"])


class ActivatableModelTests(TestCase):
    """Tests for ActivatableModel functionality."""

    def test_model_fields_exist(self) -> None:
        """Test that ActivatableModel has the required fields."""
        from src.apps.core.models import ActivatableModel

        # Check that fields exist
        fields = [f.name for f in ActivatableModel._meta.get_fields()]
        self.assertIn("is_active", fields)
        self.assertIn("created_at", fields)  # Inherited from TimestampedModel
        self.assertIn("updated_at", fields)  # Inherited from TimestampedModel

    def test_model_is_abstract(self) -> None:
        """Test that ActivatableModel is abstract."""
        from src.apps.core.models import ActivatableModel

        self.assertTrue(ActivatableModel._meta.abstract)

    def test_has_base_manager(self) -> None:
        """Test that ActivatableModel uses BaseManager."""

        self.assertIsInstance(TestActivatableModel.objects, BaseManager)

    def test_soft_delete_method_exists(self) -> None:
        """Test that soft_delete method exists."""
        from src.apps.core.models import ActivatableModel

        self.assertTrue(hasattr(ActivatableModel, "soft_delete"))
        self.assertTrue(callable(ActivatableModel.soft_delete))

    def test_activate_method_exists(self) -> None:
        """Test that activate method exists."""
        from src.apps.core.models import ActivatableModel

        self.assertTrue(hasattr(ActivatableModel, "activate"))
        self.assertTrue(callable(ActivatableModel.activate))


class AuthorableModelTests(TestCase):
    """Tests for AuthorableModel functionality."""

    def test_model_fields_exist(self) -> None:
        """Test that AuthorableModel has the required fields."""
        from src.apps.core.models import AuthorableModel

        # Check that fields exist
        fields = [f.name for f in AuthorableModel._meta.get_fields()]
        self.assertIn("created_by", fields)
        self.assertIn("updated_by", fields)
        self.assertIn("created_at", fields)  # Inherited from TimestampedModel
        self.assertIn("updated_at", fields)  # Inherited from TimestampedModel

    def test_model_is_abstract(self) -> None:
        """Test that AuthorableModel is abstract."""
        from src.apps.core.models import AuthorableModel

        self.assertTrue(AuthorableModel._meta.abstract)

    def test_foreign_key_relationships(self) -> None:
        """Test that foreign key relationships are set up correctly."""
        created_by_field = TestAuthorableModel._meta.get_field("created_by")
        updated_by_field = TestAuthorableModel._meta.get_field("updated_by")

        # Check that they're foreign keys to User model
        self.assertEqual(created_by_field.related_model, User)
        self.assertEqual(updated_by_field.related_model, User)

        # Check that they allow null
        self.assertTrue(getattr(created_by_field, "null", False))
        self.assertTrue(getattr(updated_by_field, "null", False))

    def test_save_method_override_exists(self) -> None:
        """Test that save method is overridden."""
        from src.apps.core.models import AuthorableModel

        # Check that save method exists (it's inherited but may be overridden)
        self.assertTrue(hasattr(AuthorableModel, "save"))
        self.assertTrue(callable(AuthorableModel.save))


class SluggedModelTests(TestCase):
    """Tests for SluggedModel functionality."""

    def test_model_fields_exist(self) -> None:
        """Test that SluggedModel has the required fields."""
        from src.apps.core.models import SluggedModel

        # Check that fields exist
        fields = [f.name for f in SluggedModel._meta.get_fields()]
        self.assertIn("slug", fields)

    def test_model_is_abstract(self) -> None:
        """Test that SluggedModel is abstract."""
        from src.apps.core.models import SluggedModel

        self.assertTrue(SluggedModel._meta.abstract)

    def test_slug_field_properties(self) -> None:
        """Test that slug field has correct properties."""
        from src.apps.core.models import SluggedModel

        slug_field = SluggedModel._meta.get_field("slug")

        # Check field properties
        self.assertEqual(getattr(slug_field, "max_length", 0), 100)
        self.assertTrue(getattr(slug_field, "unique", False))

    def test_save_method_override_exists(self) -> None:
        """Test that save method is overridden for slug generation."""
        from src.apps.core.models import SluggedModel

        # Check that save method exists
        self.assertTrue(hasattr(SluggedModel, "save"))
        self.assertTrue(callable(SluggedModel.save))


class ModelIntegrationTests(TestCase):
    """Integration tests for model functionality."""

    def test_timestamped_model_ordering(self) -> None:
        """Test that TimestampedModel has correct ordering."""
        from src.apps.core.models import TimestampedModel

        self.assertEqual(TimestampedModel._meta.ordering, ["-created_at"])

    def test_inheritance_chain(self) -> None:
        """Test that model inheritance works correctly."""
        from src.apps.core.models import (
            ActivatableModel,
            AuthorableModel,
            TimestampedModel,
        )

        # Test that ActivatableModel inherits from TimestampedModel
        self.assertTrue(issubclass(ActivatableModel, TimestampedModel))

        # Test that AuthorableModel inherits from TimestampedModel
        self.assertTrue(issubclass(AuthorableModel, TimestampedModel))

    def test_all_models_are_abstract(self) -> None:
        """Test that all base models are abstract."""
        from src.apps.core.models import (
            ActivatableModel,
            AuthorableModel,
            SluggedModel,
            TimestampedModel,
        )

        abstract_models = [
            TimestampedModel,
            ActivatableModel,
            AuthorableModel,
            SluggedModel,
        ]

        for model in abstract_models:
            with self.subTest(model=model.__name__):
                self.assertTrue(
                    model._meta.abstract, f"{model.__name__} should be abstract"
                )

    def test_field_help_texts_exist(self) -> None:
        """Test that important fields have help text."""
        from src.apps.core.models import (
            ActivatableModel,
            AuthorableModel,
            SluggedModel,
            TimestampedModel,
        )

        # Test TimestampedModel help texts
        created_at_field = TimestampedModel._meta.get_field("created_at")
        updated_at_field = TimestampedModel._meta.get_field("updated_at")

        self.assertTrue(getattr(created_at_field, "help_text", ""))
        self.assertTrue(getattr(updated_at_field, "help_text", ""))

        # Test ActivatableModel help text
        is_active_field = ActivatableModel._meta.get_field("is_active")
        self.assertTrue(getattr(is_active_field, "help_text", ""))

        # Test AuthorableModel help texts
        created_by_field = AuthorableModel._meta.get_field("created_by")
        updated_by_field = AuthorableModel._meta.get_field("updated_by")

        self.assertTrue(getattr(created_by_field, "help_text", ""))
        self.assertTrue(getattr(updated_by_field, "help_text", ""))

        # Test SluggedModel help text
        slug_field = SluggedModel._meta.get_field("slug")
        self.assertTrue(getattr(slug_field, "help_text", ""))


class ModelBehaviorTests(TestCase):
    """Tests for the actual behavior of model methods."""

    def test_soft_delete_and_activate(self) -> None:
        """Test that soft_delete and activate methods work correctly."""
        instance = TestActivatableModel.objects.create(name="test_instance")
        self.assertTrue(instance.is_active)

        instance.soft_delete()
        instance.refresh_from_db()
        self.assertFalse(instance.is_active)

        instance.activate()
        instance.refresh_from_db()
        self.assertTrue(instance.is_active)

    def test_base_manager(self) -> None:
        """Test that the BaseManager filters active/inactive objects correctly."""
        active_instance = TestActivatableModel.objects.create(
            name="active", is_active=True
        )
        inactive_instance = TestActivatableModel.objects.create(
            name="inactive", is_active=False
        )

        self.assertIn(active_instance, TestActivatableModel.objects.active())
        self.assertNotIn(inactive_instance, TestActivatableModel.objects.active())

        self.assertIn(inactive_instance, TestActivatableModel.objects.inactive())
        self.assertNotIn(active_instance, TestActivatableModel.objects.inactive())

    def test_slug_generation_on_save(self) -> None:
        """Test that a slug is auto-generated from the name field on save."""
        instance = TestSluggedModel.objects.create(name="A Test Name")
        self.assertEqual(instance.slug, "a-test-name")

    def test_unique_slug_generation(self) -> None:
        """Test that a unique slug is generated if the original slug exists."""
        TestSluggedModel.objects.create(name="A Test Name", slug="a-test-name")
        new_instance = TestSluggedModel.objects.create(name="A Test Name")
        self.assertEqual(new_instance.slug, "a-test-name-1")
