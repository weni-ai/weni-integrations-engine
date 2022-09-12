from rest_framework.renderers import JSONRenderer
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated

from marketplace.internal.authenticators import InternalOIDCAuthentication
from marketplace.internal.permissions import CanCommunicateInternally


class InternalGenericViewSet(GenericViewSet):
    authentication_classes = [InternalOIDCAuthentication]
    permission_classes = [IsAuthenticated, CanCommunicateInternally]
    renderer_classes = [JSONRenderer]
    throttle_classes = []
