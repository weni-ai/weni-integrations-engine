# Generated by Django 3.2.4 on 2021-09-01 19:23

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0007_alter_app_project_uuid"),
    ]

    operations = [
        migrations.RenameField(
            model_name="app",
            old_name="app_code",
            new_name="code",
        ),
        migrations.RenameField(
            model_name="apptypeasset",
            old_name="app_code",
            new_name="code",
        ),
    ]
