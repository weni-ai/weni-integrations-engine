import uuid
from typing import TYPE_CHECKING

from django.utils import timezone
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

from marketplace.core.validators import validate_app_code_exists


if TYPE_CHECKING:
    from marketplace.core.types.base import AppType


class BaseModel(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_on = models.DateTimeField(
        _("Created on"), editable=False, auto_now_add=True
    )
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

    def clean(self):
        if self.id and not self.modified_by:
            raise ValidationError(_("The field 'modified_by' can't be None"))

    class Meta:
        abstract = True

    @property
    def edited(self) -> bool:
        return bool(self.modified_by)


class AppTypeBaseModel(BaseModel):
    code = models.SlugField(validators=[validate_app_code_exists])

    @property
    def apptype(self) -> "AppType":
        """
        Returns the respective AppType
        """
        from marketplace.core.types import APPTYPES

        try:
            return APPTYPES.get(self.code)
        except KeyError:
            return APPTYPES.get("generic")

    class Meta:
        abstract = True


class Prompt(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    text = models.TextField()
    app = models.ForeignKey(
        "applications.App", on_delete=models.PROTECT, related_name="prompts"
    )
    created_on = models.DateTimeField(
        "Created on", editable=False, default=timezone.now
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="created_%(class)ss",
        null=True,
    )

    class Meta:
        db_table = "chatgpt_prompt"
