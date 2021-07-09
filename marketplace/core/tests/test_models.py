from django.db import connection
from django.db.models.base import ModelBase
from django.db.utils import ProgrammingError
from django.test import TestCase
from django.contrib.auth import get_user_model

from marketplace.core.models import BaseModel


User = get_user_model()


class TestBaseModel(TestCase):
    def setUp(self):
        super().setUp()

        self.fakemodel = self.__class__._base_model
        self.user = User.objects.create_superuser(email="admin@marketplace.ai", password="fake@pass#$")

        self.fakemodel_instance = self.fakemodel.objects.create(created_by=self.user)

    @classmethod
    def setUpClass(cls):
        if not hasattr(cls, "_base_model"):
            cls._base_model = ModelBase("FakeModel", (BaseModel,), {"__module__": BaseModel.__module__})

        try:
            with connection.schema_editor() as schema_editor:
                schema_editor.create_model(cls._base_model)
            super(TestBaseModel, cls).setUpClass()
        except ProgrammingError:
            pass

    @classmethod
    def tearDownClass(cls):
        try:
            with connection.schema_editor() as schema_editor:
                schema_editor.delete_model(cls._base_model)
            super(TestAbstractBaseModel, cls).tearDownClass()
        except ProgrammingError:
            pass

    def test_model_have_right_related_names(self):
        self.assertTrue(hasattr(self.user, "created_fakemodels"))
        self.assertTrue(hasattr(self.user, "modified_fakemodels"))

    def test_created_by_right_user(self):
        self.assertEqual(self.fakemodel_instance.created_by, self.user)
        self.assertEqual(self.user.created_fakemodels.first(), self.fakemodel_instance)

    def test_modfied_by_is_none(self):
        self.assertIsNone(self.fakemodel_instance.modified_by)

    def test_change_instance_without_modified_by(self):
        with self.assertRaises(ValueError):
            self.fakemodel_instance.save()

    def test_change_instance_with_modified_by(self):
        self.fakemodel_instance.modified_by = self.user
        self.fakemodel_instance.save()

        self.assertEqual(self.fakemodel_instance.modified_by, self.user)
        self.assertEqual(self.user.modified_fakemodels.first(), self.fakemodel_instance)
