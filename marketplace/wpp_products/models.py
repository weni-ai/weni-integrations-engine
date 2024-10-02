from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import JSONField, Max, QuerySet

from typing import Optional

from marketplace.core.models import BaseModel
from marketplace.applications.models import App


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


class Product(BaseModel):  # Model currently unused
    AVAILABILITY_CHOICES = [("in stock", "in stock"), ("out of stock", "out of stock")]
    CONDITION_CHOICES = [
        ("new", "new"),
        ("refurbished", "refurbished"),
        ("used", "used"),
    ]
    facebook_product_id = models.CharField(max_length=100)
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


class UploadProduct(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("success", "Success"),
        ("error", "Error"),
    ]
    facebook_product_id = models.CharField(max_length=100)
    data = JSONField()
    catalog = models.ForeignKey(
        Catalog, on_delete=models.PROTECT, related_name="upload_catalog"
    )
    feed = models.ForeignKey(
        ProductFeed,
        on_delete=models.PROTECT,
        related_name="upload_feed",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, default="pending", choices=STATUS_CHOICES)
    modified_on = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["catalog", "feed", "status"]),
            models.Index(fields=["facebook_product_id"]),
            models.Index(fields=["modified_on"]),
        ]

    @classmethod
    def remove_duplicates(cls, catalog: Catalog) -> None:
        """Removes duplicate products for a given catalog, keeping the most recent ones."""
        # Get all duplicate records in the catalog
        duplicates = (
            cls.objects.filter(catalog=catalog)
            .values("facebook_product_id")
            .annotate(count=models.Count("id"))
            .filter(count__gt=1)
        )

        for duplicate in duplicates:
            print(
                f"Found duplicate entries for facebook_product_id: {duplicate['facebook_product_id']}"
            )
            # Get all records for the duplicate facebook_product_id, ordered by most recent first
            duplicate_records = cls.objects.filter(
                facebook_product_id=duplicate["facebook_product_id"],
                catalog=catalog,
            ).order_by(
                "-modified_on"
            )  # Order by newest first

            # Exclude the most recent record and delete all others
            most_recent_record = duplicate_records.first()
            cls.objects.filter(
                facebook_product_id=duplicate["facebook_product_id"],
                catalog=catalog,
            ).exclude(id=most_recent_record.id).delete()

            print(
                f"Deleted all but the most recent record with ID {most_recent_record.id}"
            )

    @classmethod
    def get_latest_products(
        cls, catalog: Catalog, status: str = "pending", batch_size: Optional[int] = None
    ) -> QuerySet:
        """Fetches the most recent product for each facebook_product_id."""
        query = (
            cls.objects.filter(catalog=catalog, status=status)
            .values("facebook_product_id")
            .annotate(latest_id=Max("id"))
            .values_list("latest_id", flat=True)
        )
        if batch_size:
            query = query[:batch_size]

        product_ids = list(query)
        return cls.objects.filter(id__in=product_ids)


class WebhookLog(models.Model):
    sku_id = models.IntegerField()
    data = JSONField()
    created_on = models.DateTimeField(auto_now=True)
    vtex_app = models.ForeignKey(
        App,
        on_delete=models.CASCADE,
        related_name="vtex_webhook_logs",
        blank=True,
        null=True,
        limit_choices_to={"code": "vtex"},
    )


class ProductUploadLog(models.Model):
    sku_id = models.IntegerField()
    created_on = models.DateTimeField(auto_now=True)
    vtex_app = models.ForeignKey(
        App,
        on_delete=models.CASCADE,
        related_name="vtex_product_upload_logs",
        blank=True,
        null=True,
        limit_choices_to={"code": "vtex"},
    )

    class Meta:
        indexes = [
            models.Index(fields=["sku_id"]),
            models.Index(fields=["created_on"]),
        ]
