"""API views for the Partner-led Account Verification flow (WhatsApp Cloud)."""

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from weni_commons.auth import WeniAuthViewMixin

from marketplace.accounts.authentication import WeniModuleAuthentication

from .dto import SubmitAccountVerificationDTO
from .permissions import AppProjectManagePermission
from .serializers import (
    AccountVerificationStateSerializer,
    SubmitAccountVerificationSerializer,
)
from .usecases import (
    GetAccountVerificationStatusUseCase,
    SubmitAccountVerificationUseCase,
)


class AccountVerificationView(WeniAuthViewMixin, APIView):
    """POST submits documents to Meta; GET returns the current state."""

    authentication_classes = [WeniModuleAuthentication]
    permission_classes = [AppProjectManagePermission]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, app_uuid):
        serializer = SubmitAccountVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dto = SubmitAccountVerificationDTO(
            app_uuid=str(app_uuid),
            documents=serializer.validated_data["documents"],
        )

        state = SubmitAccountVerificationUseCase().execute(dto)
        return Response(
            AccountVerificationStateSerializer(state.to_dict()).data,
            status=status.HTTP_201_CREATED,
        )

    def get(self, request, app_uuid):
        state = GetAccountVerificationStatusUseCase().execute(app_uuid=str(app_uuid))
        return Response(
            AccountVerificationStateSerializer(state.to_dict()).data,
            status=status.HTTP_200_OK,
        )
