import django.db.models.deletion

from django.db import migrations, models


def populate_counters(apps, schema_editor):
    """Create a zeroed counter for every existing Catalog."""
    Catalog = apps.get_model("wpp_products", "Catalog")
    CatalogUploadCounter = apps.get_model("wpp_products", "CatalogUploadCounter")

    catalog_ids = Catalog.objects.values_list("id", flat=True)
    CatalogUploadCounter.objects.bulk_create(
        [CatalogUploadCounter(catalog_id=catalog_id) for catalog_id in catalog_ids],
        ignore_conflicts=True,
        batch_size=1000,
    )


def noop_reverse(apps, schema_editor):
    """No-op reverse: dropping the table already removes the data."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("wpp_products", "0014_auto_20250912_1456"),
    ]

    operations = [
        migrations.CreateModel(
            name="CatalogUploadCounter",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("total_success", models.BigIntegerField(default=0)),
                ("total_error", models.BigIntegerField(default=0)),
                ("last_success_at", models.DateTimeField(blank=True, null=True)),
                ("last_error_at", models.DateTimeField(blank=True, null=True)),
                (
                    "catalog",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="upload_counter",
                        to="wpp_products.catalog",
                    ),
                ),
            ],
        ),
        migrations.RunPython(populate_counters, noop_reverse),
    ]
