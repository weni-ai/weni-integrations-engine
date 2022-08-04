import uuid

from django.db import models

from rest_framework.exceptions import ValidationError


class TemplateMessage(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=60)

    CATEGORY_CHOICES = (
        ("ACCOUNT_UPDATE", ""),
        ("PAYMENT_UPDATE", ""),
        ("PERSONAL_FINANCE_UPDATE", ""),
        ("SHIPPING_UPDATE", ""),
        ("RESERVATION_UPDATE", ""),
        ("ISSUE_RESOLUTION", ""),
        ("APPOINTMENT_UPDATE", ""),
        ("TRANSPORTATION_UPDATE", ""),
        ("TICKET_UPDATE", ""),
        ("ALERT_UPDATE", ""),
        ("AUTO_REPLY", ""),
        ("TRANSACTIONAL", ""),
        ("MARKETING", ""),
        ("OTP", ""),
    )

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    created_on = models.DateField()

    TEMPLATE_TYPES_CHOICES = (
        ("MEDIA", ""),
        ("INTERACTIVE", ""),
        ("TEXT", ""),
    )

    template_type = models.CharField(max_length=10, choices=TEMPLATE_TYPES_CHOICES)
    namespace = models.CharField(max_length=60)

    def verify_namespace():
        pass


class TemplateTranslation(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    STATUS_CHOICES = (
        ("APPROVED", ""),
        ("IN_APPEAL", ""),
        ("PENDING", ""),
        ("REJECTED", ""),
        ("PENDING_DELETION", ""),
        ("DELETED", ""),
        ("DISABLED", ""),
        ("LOCKED", ""),
    )

    template = models.ForeignKey(TemplateMessage, on_delete=models.PROTECT, related_name="template_translations")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    body = models.CharField(max_length=1024)
    footer = models.CharField(max_length=60)
    variable_count = models.IntegerField()
    language = models.CharField(max_length=60)
    country = models.CharField(max_length=60)
    namespace = models.CharField(max_length=60)
    external_id = models.CharField(max_length=60)


class TemplateButton(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    template_translation = models.ForeignKey(TemplateTranslation, on_delete=models.PROTECT)

    BUTTON_TYPE_CHOICES = (
        ("QUICK_REPLY", ""),
        ("PHONE_NUMBER", ""),
        ("URL", ""),
    )

    button_type = models.CharField(max_length=20, choices=BUTTON_TYPE_CHOICES)
    text = models.CharField(max_length=25)
    country_code = models.IntegerField()
    phone_number = models.CharField(max_length=20)
    url = models.CharField(max_length=2000)

    def save(self, **kwargs):
        if self.button_type == "URL" and not self.url:
            raise ValidationError("url field is required for URL button_type")

        if self.button_type == "PHONE_NUMBER" and not self.phone_number:
            raise ValidationError("phone_number field is required for PHONE_NUMBER button_type")
        super().save(**kwargs)


class TemplateHeader(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    template_translation = models.ForeignKey(TemplateTranslation, on_delete=models.PROTECT)

    HEADER_TYPE_CHOICES = (
        ("TEXT", ""),
        ("IMAGE", ""),
        ("DOCUMENT", ""),
        ("VIDEO", ""),
    )

    header_type = models.CharField(max_length=20, choices=HEADER_TYPE_CHOICES)
    text = models.CharField(max_length=60)

    def save(self, **kwargs):
        if self.header_type == "TEXT" and not self.text:
            raise ValidationError("text field is required for TEXT header_type")
        super().save(**kwargs)
