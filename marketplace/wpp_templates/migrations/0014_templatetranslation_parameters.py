from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("wpp_templates", "0013_auto_20260410_1837")]

    operations = [
        migrations.AddField(
            model_name="templatetranslation",
            name="parameter_format",
            field=models.CharField(
                blank=True,
                choices=[
                    ("NAMED", "WhatsApp.data.templates.parameter_format.named"),
                    (
                        "POSITIONAL",
                        "WhatsApp.data.templates.parameter_format.positional",
                    ),
                ],
                default=None,
                max_length=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="templatetranslation",
            name="body_named_params",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="templatetranslation",
            name="parameter_anomaly",
            field=models.JSONField(blank=True, default=None, null=True),
        ),
    ]
