# Generated by Django 3.2.4 on 2021-08-25 21:55

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0005_auto_20210820_1635"),
    ]

    operations = [
        migrations.RenameField(
            model_name="app",
            old_name="org_uuid",
            new_name="project_uuid",
        ),
        migrations.AlterField(
            model_name="app",
            name="config",
            field=models.JSONField(null=True),
        ),
    ]
