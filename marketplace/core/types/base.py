from abc import ABC, abstractproperty

from django.db.models.query import QuerySet
from rest_framework.views import APIView

from marketplace.applications.models import AppTypeAsset, App
from marketplace.interactions.models import Rating, Comment


class AbstractAppType(ABC):
    """
    Said how the child class should be structured
    """

    CATEGORY_CHANNEL = "CN"
    CATEGORY_CLASSIFIER = "CF"
    CATEGORY_TICKETER = "TK"
    CATEGORY_EXTERNAL = "EXT"

    CATEGORY_CHOICES = (
        (CATEGORY_CHANNEL, "channel"),
        (CATEGORY_CLASSIFIER, "classifier"),
        (CATEGORY_TICKETER, "ticketer"),
        (CATEGORY_EXTERNAL, "external"),
    )

    @abstractproperty
    def view_class(self) -> APIView:
        ...  # pragma: no cover

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

    @abstractproperty
    def platform(self) -> str:
        ...  # pragma: no cover


class AppType(AbstractAppType):
    """
    Abstract class that all app types must inherit from it
    """

    def __init__(self):
        if self.view_class is not None:
            self.view_class.type_class = self

    @property
    def assets(self) -> QuerySet:
        return AppTypeAsset.objects.filter(code=self.code)

    @property
    def apps(self) -> QuerySet:
        return App.objects.filter(code=self.code)

    @property
    def ratings(self) -> QuerySet:
        return Rating.objects.filter(code=self.code)

    @property
    def comments(self) -> QuerySet:
        return Comment.objects.filter(code=self.code)

    def get_icon_asset(self) -> AppTypeAsset:
        try:
            return self.assets.get(asset_type=AppTypeAsset.ASSET_TYPE_ICON)
        except AppTypeAsset.DoesNotExist:
            return None

    def get_icon_url(self) -> str:
        icon_asset = self.get_icon_asset()
        if icon_asset is not None:
            return self.get_icon_asset().attachment.url

    def get_category_display(self) -> str:
        categories = dict(self.CATEGORY_CHOICES)
        return categories.get(self.category)

    def get_ratings_average(self) -> float:
        return Rating.get_apptype_average(self.code)

    def can_add(self, project_uuid: str) -> bool:
        return True

    def create_app(self, *args, **kwargs) -> App:
        return App.objects.create(*args, **kwargs, code=self.code, platform=self.platform)

    def template_type_setup(self) -> dict:
        raise NotImplementedError(f"App: {self.name} cannot be configured from a project template!")
