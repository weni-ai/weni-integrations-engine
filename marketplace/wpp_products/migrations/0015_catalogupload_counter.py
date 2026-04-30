import django.db.models.deletion

from django.db import migrations, models


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
    ]
