import random
from datetime import timedelta

from django.conf import settings as django_settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import views

from marketplace.applications.serializers import AppTypeSerializer, MyAppSerializer
from marketplace.core import types
from marketplace.applications.models import App, AppTypeFeatured
from marketplace.accounts.models import ProjectAuthorization
from marketplace.accounts.permissions import is_crm_user
from marketplace.internal.permissions import CanCommunicateInternally
from marketplace.clients.facebook.client import FacebookClient
from marketplace.clients.exceptions import CustomAPIException


class AppTypeViewSet(viewsets.ViewSet):
    serializer_class = AppTypeSerializer

    def get_serializer_context(self):
        return {"request": self.request}

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = {"request": self.request}
        return self.serializer_class(*args, **kwargs)

    def list(self, request):
        category = request.query_params.get("category", None)
        apptypes = types.APPTYPES

        if category is not None:
            apptypes = apptypes.filter(
                lambda apptype: apptype.get_category_display()
                == request.query_params.get("category")
            )

        # TODO: remove the "wpp" from this filter when whatsapp leaves beta
        apptypes = apptypes.filter(
            lambda apptype: apptype.code != "wpp" and apptype.code != "generic"
        )

        serializer = self.get_serializer(apptypes.values(), many=True)

        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            apptype = types.APPTYPES.get(pk)
        except KeyError:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(apptype)

        return Response(serializer.data)

    @action(detail=False)
    def featureds(self, request, **kwargs):
        apptypes = AppTypeFeatured.get_apptype_featureds()
        serializer = self.get_serializer(apptypes, many=True)

        return Response(serializer.data)


class MyAppViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "uuid"
    serializer_class = MyAppSerializer
    queryset = App.objects
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = super().get_queryset()

        query_params = self.request.query_params
        project_uuid = query_params.get("project_uuid")
        configured = query_params.get("configured")

        if not project_uuid:
            raise ValidationError("project_uuid is a required parameter!")

        user = self.request.user

        if not is_crm_user(user):
            try:
                user.authorizations.get(project_uuid=project_uuid)
            except ProjectAuthorization.DoesNotExist:
                raise PermissionDenied()

        queryset = queryset.filter(project_uuid=project_uuid)

        if configured is not None:
            if configured == "true":
                queryset = queryset.filter(configured=True)

            elif configured == "false":
                queryset = queryset.filter(configured=False)

            else:
                raise ValidationError(
                    f"Expected a boolean param in configured, but recived `{configured}`"
                )

        return queryset


class CheckAppIsIntegrated(views.APIView):
    permission_classes = [CanCommunicateInternally]

    def get(self, request):
        project_uuid = request.query_params.get("project_uuid", None)

        if not project_uuid:
            return Response(
                {"error": "project_uuid is required on query params"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        apps = App.objects.filter(code="wpp-cloud", project_uuid=project_uuid)

        if not apps.exists():
            return Response(
                {
                    "message": "Project with whatsapp integrations not exists",
                    "data": {"has_whatsapp": False},
                }
            )

        app = apps.first()

        return Response(
            {
                "message": "Project with whatsapp integrations exists",
                "data": {
                    "has_whatsapp": True,
                    "wpp_cloud_app_uuid": str(app.uuid),
                    "flows_channel_uuid": str(app.flow_object_uuid),
                    "phone_number": app.config.get("wa_number"),
                },
            },
            status=status.HTTP_200_OK,
        )


class PreverifiedPhoneNumber(views.APIView):
    """
    Returns a random pre-verified phone number from the BSP business for
    embedded signup. Cache stores the list from Meta plus IDs already chosen
    in the last 5 minutes, so we avoid returning the same number twice in that
    window (e.g. concurrent requests). After 5 min the cache is rebuilt from Meta.
    """

    permission_classes = [CanCommunicateInternally]
    CACHE_KEY = "preverified_numbers"
    CACHE_TTL_SECONDS = 300  # 5 minutes

    def get(self, request):
        business_id = getattr(
            django_settings, "WHATSAPP_BSP_BUSINESS_ID", ""
        ).strip()
        if not business_id:
            return Response(
                {
                    "error": "WHATSAPP_BSP_BUSINESS_ID is not configured",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        cached = cache.get(self.CACHE_KEY)
        now = timezone.now()
        if cached is None or (cached.get("expires_at") and now > cached["expires_at"]):
            try:
                client = FacebookClient(
                    django_settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN
                )
                response = client.get_preverified_numbers()
            except CustomAPIException as e:
                meta_status = getattr(e, "status_code", None)
                meta_detail = e.detail
                if not isinstance(meta_detail, dict):
                    meta_detail = {"error": str(meta_detail) if meta_detail else "Failed to fetch preverified numbers from Meta"}
                if meta_status == 429:
                    return Response(meta_detail, status=status.HTTP_429_TOO_MANY_REQUESTS)
                if meta_status == 500:
                    return Response(meta_detail, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                return Response(
                    meta_detail,
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            except Exception:
                return Response(
                    {"error": "Internal server error"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            data_list = response.get("data") or []
            cached = {
                "data_list": data_list,
                "chosen_ids": [],
                "expires_at": now + timedelta(seconds=self.CACHE_TTL_SECONDS),
            }
            cache.set(self.CACHE_KEY, cached, timeout=self.CACHE_TTL_SECONDS + 60)

        data_list = cached.get("data_list") or []
        chosen_ids = set(cached.get("chosen_ids") or [])
        available = [i for i in data_list if i.get("id") not in chosen_ids]

        if not available:
            return Response({"data": []}, status=status.HTTP_200_OK)

        chosen = random.choice(available)
        chosen_id = chosen["id"]
        chosen_ids.add(chosen_id)
        remaining = getattr(cache, "ttl", lambda k: None)(self.CACHE_KEY)
        cache.set(
            self.CACHE_KEY,
            {**cached, "chosen_ids": list(chosen_ids)},
            timeout=remaining if remaining and remaining > 0 else self.CACHE_TTL_SECONDS + 60,
        )
        return Response({"data": [chosen_id]}, status=status.HTTP_200_OK)
