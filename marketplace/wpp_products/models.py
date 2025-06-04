from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import JSONField, QuerySet, Subquery, OuterRef


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
    priority = models.IntegerField(default=0)

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

        if duplicates:
            print(
                f"Found duplicate entries for catalog : {catalog.name}, Deleted all but the most recent records"
            )
        for duplicate in duplicates:
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

    @classmethod
    def get_latest_products(
        cls, catalog: Catalog, status: str = "pending", batch_size: Optional[int] = None
    ) -> QuerySet:
        """
        Fetches the most relevant product for each unique `facebook_product_id`,
        prioritizing entries with higher `priority`, and within the same priority,
        selecting the most recently modified entry.

        This ensures:
        - Only one product is returned per `facebook_product_id`
        - Preference is given to `priority=1` over `priority=0`
        - Among entries with the same priority, the latest `modified_on` is chosen

        Args:
            catalog (Catalog): The catalog to filter products for.
            status (str, optional): The processing status to filter on. Default is "pending".
            batch_size (int, optional): Limits the number of products returned.

        Returns:
            QuerySet: A queryset of the most relevant UploadProduct instances.
        """
        inner_query = (
            cls.objects.filter(
                catalog=catalog,
                status=status,
                facebook_product_id=OuterRef("facebook_product_id"),
            )
            .order_by("-priority", "-modified_on")
            .values("id")[:1]
        )

        ids = (
            cls.objects.filter(catalog=catalog, status=status)
            .values("facebook_product_id")
            .annotate(best_id=Subquery(inner_query))
            .values_list("best_id", flat=True)
        )

        if batch_size:
            ids = ids[:batch_size]

        return cls.objects.filter(id__in=list(ids))


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


class ProductValidation(models.Model):
    catalog = models.ForeignKey(
        Catalog, on_delete=models.CASCADE, related_name="product_validations"
    )
    sku_id = models.IntegerField()
    is_valid = models.BooleanField(default=True)
    classification = models.CharField(max_length=100)
    description = models.CharField(max_length=9999, null=True, blank=True)
    modified_on = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product Validation"
        verbose_name_plural = "Product Validations"
        unique_together = ("catalog", "sku_id")

        indexes = [
            models.Index(fields=["catalog"]),
            models.Index(fields=["sku_id"]),
        ]

    def __str__(self):
        return f"{self.catalog.name} - {self.sku_id} - {'Valid' if self.is_valid else 'Invalid'}"
