from django.test import TestCase
from django.contrib.auth import get_user_model
import uuid
from marketplace.services.vtex.app_manager import AppVtexManager
from marketplace.services.vtex.exceptions import (
    NoVTEXAppConfiguredException,
    MultipleVTEXAppsConfiguredException,
)
from marketplace.applications.models import App
from marketplace.projects.models import Project


User = get_user_model()


class TestAppVtexManager(TestCase):
    def setUp(self):
        self.manager = AppVtexManager()

        # Create test user and project
        self.user = User.objects.create_user(email="test@example.com")
        self.project = Project.objects.create(
            name="Test Project", uuid=str(uuid.uuid4()), created_by=self.user
        )

    def test_get_vtex_app_or_error_not_found(self):
        """Test when VTEX app is not found"""
        with self.assertRaises(NoVTEXAppConfiguredException):
            self.manager.get_vtex_app_or_error(self.project.uuid)

    def test_get_vtex_app_or_error_success(self):
        """Test successful app retrieval"""
        # Create a VTEX app
        app = App.objects.create(
            code="vtex",
            project_uuid=str(self.project.uuid),
            configured=True,
            uuid="550e8400-e29b-41d4-a716-446655440123",
            created_by=self.user,
        )

        result = self.manager.get_vtex_app_or_error(self.project.uuid)

        self.assertEqual(result, app)

    def test_get_vtex_app_or_error_multiple_found(self):
        """Test when multiple VTEX apps are found"""
        # Create multiple VTEX apps
        App.objects.create(
            code="vtex",
            project_uuid=str(self.project.uuid),
            configured=True,
            uuid="550e8400-e29b-41d4-a716-446655440001",
            created_by=self.user,
        )
        App.objects.create(
            code="vtex",
            project_uuid=str(self.project.uuid),
            configured=True,
            uuid="550e8400-e29b-41d4-a716-446655440002",
            created_by=self.user,
        )

        with self.assertRaises(MultipleVTEXAppsConfiguredException):
            self.manager.get_vtex_app_or_error(self.project.uuid)

    def test_initial_sync_products_completed_success(self):
        """Test successful initial sync completion"""
        app = App.objects.create(
            code="vtex",
            project_uuid=str(self.project.uuid),
            configured=True,
            uuid="550e8400-e29b-41d4-a716-446655440123",
            config={},
            created_by=self.user,
        )

        result = self.manager.initial_sync_products_completed(app)

        app.refresh_from_db()
        self.assertTrue(result)
        self.assertTrue(app.config["initial_sync_completed"])

    def test_update_vtex_ads(self):
        """Test updating VTEX ads configuration"""
        app = App.objects.create(
            code="vtex",
            project_uuid=str(self.project.uuid),
            configured=True,
            uuid="550e8400-e29b-41d4-a716-446655440123",
            config={},
            created_by=self.user,
        )

        vtex_ads = {"ad1": "value1", "ad2": "value2"}

        self.manager.update_vtex_ads(app, vtex_ads)

        app.refresh_from_db()
        self.assertEqual(app.config["vtex_ads"], vtex_ads)

    def test_get_vtex_app_uuid_generates_unique_uuid(self):
        """Test UUID generation creates unique UUIDs"""
        uuid1 = self.manager.get_vtex_app_uuid()
        uuid2 = self.manager.get_vtex_app_uuid()

        self.assertNotEqual(uuid1, uuid2)
        self.assertIsInstance(uuid1, str)
        self.assertIsInstance(uuid2, str)
        self.assertEqual(len(uuid1), 36)  # UUID4 length
        self.assertEqual(len(uuid2), 36)  # UUID4 length
