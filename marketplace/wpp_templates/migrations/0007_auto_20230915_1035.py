# Generated by Django 3.2.4 on 2023-09-15 13:35

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wpp_templates", "0006_templatetranslation_message_template_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="templatebutton",
            name="autofill_text",
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="templatebutton",
            name="otp_type",
            field=models.CharField(
                choices=[("COPY_CODE", "Copy Code"), ("ONE_TAP", "One Tap")],
                max_length=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="templatebutton",
            name="package_name",
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="templatebutton",
            name="signature_hash",
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="templatebutton",
            name="button_type",
            field=models.CharField(
                choices=[
                    ("QUICK_REPLY", "WhatsApp.data.templates.buttons.type.quick_reply"),
                    (
                        "PHONE_NUMBER",
                        "WhatsApp.data.templates.buttons.type.phone_number",
                    ),
                    ("URL", "WhatsApp.data.templates.buttons.type.url"),
                    ("OTP", "WhatsApp.data.templates.buttons.type.otp"),
                ],
                max_length=20,
            ),
        ),
    ]