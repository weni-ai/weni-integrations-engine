# Generated by Django 3.2.4 on 2023-12-29 15:21

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wpp_products", "0004_product_productfeed"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="facebook_product_id",
            field=models.CharField(max_length=30),
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.UniqueConstraint(
                fields=("facebook_product_id", "catalog"),
                name="unique_facebook_product_id_per_catalog",
            ),
        ),
    ]
