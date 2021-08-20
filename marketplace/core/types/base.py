from typing import Dict
from abc import ABC, abstractproperty

from django.db.models.query import QuerySet

from marketplace.applications.models import AppTypeAsset, App
from marketplace.interactions.models import Rating, Comment


class AbstractAppType(ABC):
    """
    Said how the child class should be structured
    """

    CATEGORY_CHANNEL = "CN"
    CATEGORY_CLASSIFIER = "CF"
    CATEGORY_TICKETER = "TK"

    CATEGORY_CHOICES = (
        (CATEGORY_CHANNEL, "channel"),
        (CATEGORY_CLASSIFIER, "classifier"),
        (CATEGORY_TICKETER, "ticketer"),
    )

    @abstractproperty
    def code(self) -> str:
        ...  # pragma: no cover

    @abstractproperty
    def name(self) -> str:
        ...  # pragma: no cover

    @abstractproperty
    def description(self) -> str:
        ...  # pragma: no cover

    @abstractproperty
    def summary(self) -> str:
        ...  # pragma: no cover

    @abstractproperty
    def category(self) -> str:
        ...  # pragma: no cover

    @abstractproperty
    def developer(self) -> str:
        ...  # pragma: no cover

    @abstractproperty
    def bg_color(self) -> str:
        ...  # pragma: no cover


class AppType(AbstractAppType):
    """
    Abstract class that all app types must inherit from it
    """

    @property
    def assets(self) -> QuerySet:
        return AppTypeAsset.objects.filter(app_code=self.code)

    @property
    def apps(self) -> QuerySet:
        return App.objects.filter(app_code=self.code)

    @property
    def ratings(self) -> QuerySet:
        return Rating.objects.filter(app_code=self.code)

    @property
    def comments(self) -> QuerySet:
        return Comment.objects.filter(app_code=self.code)

    def get_icon_asset(self) -> AppTypeAsset:
        try:
            return self.assets.get(asset_type=AppTypeAsset.ASSET_TYPE_ICON)
        except AppTypeAsset.DoesNotExist:
            raise AppTypeAsset.DoesNotExist(f"{self.__class__.__name__} doesn't have an icon")

    def get_icon_url(self) -> str:
        return self.get_icon_asset().attachment.url

    def get_category_display(self) -> str:
        categories = dict(self.CATEGORY_CHOICES)
        return categories.get(self.category)

    def get_ratings_average(self) -> float:
        return Rating.get_apptype_average(self.code)
