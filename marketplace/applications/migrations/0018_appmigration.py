from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("applications", "0017_alter_app_platform"),
    ]

    operations = [
        migrations.CreateModel(
            name="AppMigration",
            fields=[
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="UUID",
                    ),
                ),
                (
                    "flow_object_uuid",
                    models.UUIDField(verbose_name="flow object UUID"),
                ),
                (
                    "project_from",
                    models.UUIDField(verbose_name="source project UUID"),
                ),
                (
                    "project_to",
                    models.UUIDField(verbose_name="destination project UUID"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "pending"),
                            ("PUBLISH_FAILED", "publish failed"),
                            ("IN_PROGRESS", "in progress"),
                            ("PARTIAL_ERROR", "partial error"),
                            ("COMPLETED", "completed"),
                        ],
                        default="PENDING",
                        max_length=20,
                        verbose_name="status",
                    ),
                ),
                (
                    "modules_status",
                    models.JSONField(
                        blank=True, default=dict, verbose_name="modules status"
                    ),
                ),
                (
                    "requested_by",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        null=True,
                        verbose_name="requested by",
                    ),
                ),
                (
                    "published_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="published at"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="created at"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="updated at"),
                ),
                (
                    "app",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="migrations",
                        to="applications.app",
                    ),
                ),
            ],
            options={
                "verbose_name": "app migration",
                "verbose_name_plural": "app migrations",
            },
        ),
        migrations.AddIndex(
            model_name="appmigration",
            index=models.Index(
                fields=["app", "status"], name="appmigration_app_status"
            ),
        ),
    ]
