import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _

from marketplace.core.validators import validate_app_code_exists


class BaseModel(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_on = models.DateTimeField(_("Created on"), editable=False, auto_now_add=True)
    modified_on = models.DateTimeField(_("Modified on"), auto_now=True)

    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="created_%(class)ss",
    )
    modified_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="modified_%(class)ss",
        blank=True,
        null=True,
    )

    def save(self, *args, **kwargs):
        if self.id and not self.modified_by:
            raise ValueError("modified_by can't be None")

        super().save(*args, **kwargs)

    class Meta:
        abstract = True

    @property
    def edited(self) -> bool:
        return bool(self.modified_by)


class AppTypeBaseModel(BaseModel):

    app_code = models.SlugField(validators=[validate_app_code_exists])

    class Meta:
        abstract = True
