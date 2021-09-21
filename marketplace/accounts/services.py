from django_grpc_framework import generics, mixins


class UserPermissionService(mixins.UpdateModelMixin, generics.GenericService):
    def Update(self, request, context):
        return super().Update(request, context)
