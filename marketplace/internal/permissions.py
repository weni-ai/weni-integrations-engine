from rest_framework import permissions


class CanCommunicateInternally(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.user_permissions.filter(codename="can_communicate_internally").exists()
