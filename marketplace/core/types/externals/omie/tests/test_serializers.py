from uuid import uuid4
from unittest.mock import MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model

from ..serializers import OmieConfigureSerializer
from ..type import OmieType


User = get_user_model()


class XTestCase(TestCase):

    def setUp(self):
        super().setUp()
        self.app_type = OmieType()
        self.user = User.objects.get_admin_user()
        self.app = self.app_type.create_app(project_uuid=uuid4(), created_by=self.user)

    def test_x(self):

        response_mock = MagicMock(status_code=201)
        response_mock.json.return_value = {"uuid": uuid4()}

        client_mock = MagicMock()
        client_mock.create_external_service.return_value = response_mock

        serializer = OmieConfigureSerializer(client=client_mock)
        print(serializer)
