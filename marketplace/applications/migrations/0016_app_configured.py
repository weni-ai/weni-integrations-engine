# Generated by Django 3.2.4 on 2023-08-03 16:22

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0015_apptypefeatured_priority"),
    ]

    operations = [
        migrations.AddField(
            model_name="app",
            name="configured",
            field=models.BooleanField(default=False),
        ),
    ]