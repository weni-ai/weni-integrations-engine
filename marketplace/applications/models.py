from django.db import models
from django.utils.translation import ugettext_lazy as _

from marketplace.core.models import AbstractBaseModel


class App(AbstractBaseModel):

    PLATFORM_IA = "IA"
    PLATFORM_WENI_FLOWS = "WF"
    PLATFORM_RC = "RC"

    PLATFORM_CHOICES = (
        (PLATFORM_IA, "ia"),
        (PLATFORM_WENI_FLOWS, "weni-flows"),
        (PLATFORM_RC, "rc"),
    )

    config = models.JSONField()
    org_uuid = models.UUIDField("Org UUID")
    platform = models.CharField(choices=PLATFORM_CHOICES, max_length=2)
    app_slug = models.SlugField()

    class Meta:
        verbose_name = _("Org")
        verbose_name_plural = _("Orgs")

    def __str__(self) -> str:
        return self.app_slug


class AppTypeAsset(AbstractBaseModel):

    ASSET_TYPE_IMAGE_BANNER = "IB"
    ASSET_TYPE_IMAGE_COMMON = "IC"
    ASSET_TYPE_ATTACHMENT = "AT"
    ASSET_TYPE_LINK = "LK"

    ASSET_TYPE_CHOICES = (
        (ASSET_TYPE_IMAGE_BANNER, "image_banner"),
        (ASSET_TYPE_IMAGE_COMMON, "image_common"),
        (ASSET_TYPE_ATTACHMENT, "attachment"),
        (ASSET_TYPE_LINK, "link"),
    )

    app_slug = models.SlugField()
    asset_type = models.CharField("Type", choices=ASSET_TYPE_CHOICES, max_length=2)
    attachment = models.FileField()

    class Meta:
        verbose_name = "App Type Asset"
        verbose_name_plural = "App Type Assets"

    def __str__(self) -> str:
        return self.app_slug
