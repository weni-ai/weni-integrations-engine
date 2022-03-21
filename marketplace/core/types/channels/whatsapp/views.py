from typing import TYPE_CHECKING

import requests
from django.conf import settings
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status as response_status

if TYPE_CHECKING:
    from rest_framework.request import Request

from marketplace.core.types import views
from marketplace.onpremise.facades import OnPremiseQueueFacade
from marketplace.onpremise.queue import QueueItem
from marketplace.onpremise.exceptions import UnableRedeemCertificate
from marketplace.celery import app as celery_app
from .serializers import WhatsAppSerializer
from .facades import WhatsApp, WhatsAppFacade


class WhatsAppViewSet(views.BaseAppTypeViewSet):

    serializer_class = WhatsAppSerializer

    def get_queryset(self):
        return super().get_queryset().filter(code=self.type_class.code)

    def perform_create(self, serializer):
        user = self.request.user
        app_type = self.type_class

        validated_data = serializer.validated_data
        waba_id = validated_data.get("target_id")

        whatsapp: WhatsApp = None

        try:
            whatsapp_facade = WhatsAppFacade(waba_id, app_type)
            whatsapp = whatsapp_facade.create()
        except UnableRedeemCertificate as error:
            raise ValidationError(error)

        instance = serializer.save(code=self.type_class.code)

        data = dict(
            number=str(whatsapp),
            country=app_type.COUNTRY, # TODO: Use lib or API
            base_url=whatsapp.url,
            username=settings.WHATSAPP_ONPREMISE_USERNAME,
            password=whatsapp.password,
            facebook_namespace="fake",
            facebook_template_list_domain="graph.facebook.com",
            facebook_business_id="null",
            facebook_access_token="null",
        )

        task = celery_app.send_task(
            name="create_channel", args=[user.email, str(instance.project_uuid), data, instance.channeltype_code]
        )
        task.wait()
        result = task.result

        instance.config["title"] = result.get("name")
        instance.config["channelUuid"] = result.get("uuid")

        # instance.config["onpremise_url"] = onpremise_url
        instance.modified_by = user
        instance.save()

    # TODO: Send view to ompremise django app
    @action(detail=False, methods=["POST"], permission_classes=[])
    def webhook(self, request: "Request", **kwargs):
        from django.http.request import QueryDict

        data = request.data

        if isinstance(request.data, QueryDict):
            data = {key: value[0] for key, value in dict(request.data).items()}

        webhook_id = data.get("webhook_id")
        status = QueueItem.STATUS_PROPAGATING if data.get("status") == "success" else QueueItem.STATUS_FAILED
        message = data.get("message")
        # TODO: VAlidar if this code can added on InfrastructureQueueFacade
        queue = OnPremiseQueueFacade()
        item = queue.items.get(webhook_id)

        if not item:
            raise ValidationError("Invalid `webhook_id`!")

        queue.items.update(item, status=status)
        queue.items.update(item, message=message)

        return Response(status=response_status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["GET"], url_name="shared-wabas", url_path="shared-wabas")
    def shared_wabas(self, request: "Request", **kwargs):
        input_token = request.query_params.get("input_token", None)

        if input_token is None:
            raise ValidationError("input_token is a required parameter!")

        headers = {"Authorization": f"Bearer {self.type_class.SYSTEM_USER_ACCESS_TOKEN}"}

        response = requests.get(f"{self.type_class.API_URL}/debug_token?input_token={input_token}", headers=headers)
        response.raise_for_status()

        data = response.json().get("data")
        error = data.get("error")

        if error is not None:
            raise ValidationError(error.get("message"))

        granular_scopes = data.get("granular_scopes")

        try:
            scope = next(filter(lambda scope: scope.get("scope") == "whatsapp_business_management", granular_scopes))
        except StopIteration:
            return Response([])

        target_ids = scope.get("target_ids")

        wabas = []

        for target_id in target_ids:
            response = requests.get(f"{self.type_class.API_URL}/{target_id}/?access_token={input_token}")
            response.raise_for_status()

            response_json = response.json()

            waba = dict()
            waba["id"] = target_id
            waba["name"] = response_json.get("name")
            wabas.append(waba)

        return Response(wabas)
