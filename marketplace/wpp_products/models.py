from django.db import models
from marketplace.core.models import BaseModel
from marketplace.applications.models import App
from django.core.exceptions import ValidationError


class VerticalChoices(models.TextChoices):
    ECOMMERCE = "commerce", "E-commerce"
    HOTELS = "hotels", "Hotels"
    FLIGHTS = "flights", "Flights"
    DESTINATIONS = "destinations", "Destinations"
    HOME_LISTINGS = "home_listings", "Home Listings"
    VEHICLE_OFFERS = "vehicle_offers", "Vehicle Offers"
    VEHICLES = "vehicles", "Vehicles"
    OFFLINE_COMMERCE = "offline_commerce", "Offline Commerces"
    TICKETED_EXPERIENCES = "ticketed_experiences", "ticketed_experiences"


class Catalog(BaseModel):
    facebook_catalog_id = models.CharField(max_length=30)
    name = models.CharField(max_length=100)
    category = models.CharField(
        max_length=20,
        choices=VerticalChoices.choices,
        default=VerticalChoices.ECOMMERCE,
    )
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="catalogs")
    vtex_app = models.ForeignKey(
        App,
        on_delete=models.SET_NULL,
        related_name="vtex_catalogs",
        blank=True,
        null=True,
        limit_choices_to={"code": "vtex"},
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="created_catalogs",
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.name  # pragma: no cover

    def clean(self) -> None:
        super().clean()
        if self.app.code != "wpp-cloud":
            raise ValidationError("The App must be a 'WhatsApp Cloud' AppType.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["facebook_catalog_id", "app"],
                name="unique_facebook_catalog_id_per_app",
            )
        ]


class ProductFeed(BaseModel):
    facebook_feed_id = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    catalog = models.ForeignKey(Catalog, on_delete=models.CASCADE, related_name="feeds")
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.name


class Product(BaseModel):
    AVAILABILITY_CHOICES = [("in stock", "in stock"), ("out of stock", "out of stock")]
    CONDITION_CHOICES = [
        ("new", "new"),
        ("refurbished", "refurbished"),
        ("used", "used"),
    ]
    facebook_product_id = models.CharField(max_length=30)
    # facebook required fields
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=9999)
    availability = models.CharField(max_length=12, choices=AVAILABILITY_CHOICES)
    condition = models.CharField(max_length=11, choices=CONDITION_CHOICES)
    price = models.CharField(max_length=50)  # Example: "9.99 USD"
    link = models.URLField()
    image_link = models.URLField()
    brand = models.CharField(max_length=100)
    sale_price = models.CharField(max_length=50)  # Example: "9.99 USD"

    catalog = models.ForeignKey(
        Catalog, on_delete=models.CASCADE, related_name="products"
    )
    feed = models.ForeignKey(
        ProductFeed,
        on_delete=models.CASCADE,
        related_name="products",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.title

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["facebook_product_id", "catalog"],
                name="unique_facebook_product_id_per_catalog",
            )
        ]
