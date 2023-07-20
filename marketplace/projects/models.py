from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class TemplateType(models.Model):
    uuid = models.UUIDField(editable=False, unique=True)
    name = models.CharField(max_length=255)
    setup = models.JSONField(default=dict)

    def __str__(self) -> str:
        return self.name  # pragma: no cover


class Project(models.Model):
    uuid = models.UUIDField(editable=False, unique=True)
    name = models.CharField("project name", max_length=150)
    is_template = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    date_format = models.CharField(max_length=64, null=True)
    is_active = models.BooleanField(default=True)
    template_type = models.ForeignKey(TemplateType, on_delete=models.SET_NULL, null=True)
    timezone = models.CharField(max_length=64, null=True)

    def __str__(self) -> str:
        return self.name  # pragma: no cover
