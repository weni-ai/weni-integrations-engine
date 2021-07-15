from django.db import models
from django.db.models import Q
from django.db.models.constraints import UniqueConstraint
from django.utils.translation import ugettext_lazy as _

from marketplace.core.models import BaseModel


class AppBaseModel(BaseModel):

    app_code = models.SlugField()

    class Meta:
        abstract = True


class App(AppBaseModel):

    PLATFORM_IA = "IA"
    PLATFORM_WENI_FLOWS = "WF"
    PLATFORM_RC = "RC"

    PLATFORM_CHOICES = (
        (PLATFORM_IA, "inteligence-artificial"),
        (PLATFORM_WENI_FLOWS, "weni-flows"),
        (PLATFORM_RC, "rocketchat"),
    )

    config = models.JSONField()
    org_uuid = models.UUIDField("Org UUID")
    platform = models.CharField(choices=PLATFORM_CHOICES, max_length=2)

    class Meta:
        verbose_name = _("App")
        verbose_name_plural = _("Apps")

    def __str__(self) -> str:
        return self.app_code


class AppTypeAsset(AppBaseModel):

    ASSET_TYPE_IMAGE_BANNER = "IB"
    ASSET_TYPE_ICON = "IC"
    ASSET_TYPE_ATTACHMENT = "AT"
    ASSET_TYPE_LINK = "LK"

    ASSET_TYPE_CHOICES = (
        (ASSET_TYPE_IMAGE_BANNER, "image_banner"),
        (ASSET_TYPE_ICON, "icon"),
        (ASSET_TYPE_ATTACHMENT, "attachment"),
        (ASSET_TYPE_LINK, "link"),
    )

    asset_type = models.CharField("Type", choices=ASSET_TYPE_CHOICES, max_length=2)
    attachment = models.FileField()
    description = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = "App Type Asset"
        verbose_name_plural = "App Type Assets"
        constraints = [
            UniqueConstraint(
                fields=["asset_type", "app_code"],
                condition=Q(asset_type="IC"),
                name="unique_asset_type_icon_app_code",
            )
        ]

    def __str__(self) -> str:
        return self.app_code
