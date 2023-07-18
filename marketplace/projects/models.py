from django.db import models


class TemplateType(models.Model):
    uuid = models.UUIDField(editable=False, unique=True)
    name = models.CharField(max_length=255)
    setup = models.JSONField(default=dict)

    def __str__(self) -> str:
        return self.name
