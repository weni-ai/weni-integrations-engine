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
