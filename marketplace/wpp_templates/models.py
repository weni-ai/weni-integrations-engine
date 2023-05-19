import uuid
import re
import textwrap

from django.core.exceptions import ValidationError

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db import models

from marketplace.applications.models import App

User = get_user_model()


class TemplateMessage(models.Model):
    CATEGORY_CHOICES = (
        ("ACCOUNT_UPDATE", "WhatsApp.data.templates.category.account_update"),
        ("PAYMENT_UPDATE", "WhatsApp.data.templates.category.payment_update"),
        (
            "PERSONAL_FINANCE_UPDATE",
            "WhatsApp.data.templates.category.personal_finance_update",
        ),
        ("SHIPPING_UPDATE", "WhatsApp.data.templates.category.shipping_update"),
        ("RESERVATION_UPDATE", "WhatsApp.data.templates.category.reservation_update"),
        ("ISSUE_RESOLUTION", "WhatsApp.data.templates.category.issue_resolution"),
        ("APPOINTMENT_UPDATE", "WhatsApp.data.templates.category.appointment_update"),
        (
            "TRANSPORTATION_UPDATE",
            "WhatsApp.data.templates.category.transportation_update",
        ),
        ("TICKET_UPDATE", "WhatsApp.data.templates.category.ticket_update"),
        ("ALERT_UPDATE", "WhatsApp.data.templates.category.alert_update"),
        ("AUTO_REPLY", "WhatsApp.data.templates.category.auto_reply"),
        ("TRANSACTIONAL", "WhatsApp.data.templates.category.transactional"),
        ("MARKETING", "WhatsApp.data.templates.category.marketing"),
        ("OTP", "WhatsApp.data.templates.category.otp"),
        ("UTILITY", "WhatsApp.data.templates.category.utility"),
        ("AUTHENTICATION", "WhatsApp.data.templates.category.authentication"),
    )

    TEMPLATE_TYPES_CHOICES = (
        ("MEDIA", "WhatsApp.data.templates.type.media"),
        ("INTERACTIVE", "WhatsApp.data.templates.type.interactive"),
        ("TEXT", "WhatsApp.data.templates.type.text"),
    )
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    app = models.ForeignKey(App, on_delete=models.PROTECT, related_name="template")
    name = models.CharField(max_length=512)
    category = models.CharField(max_length=200, choices=CATEGORY_CHOICES)
    created_on = models.DateTimeField(
        "Created on", editable=False, default=timezone.now
    )
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="created_%(class)ss", null=True
    )
    template_type = models.CharField(max_length=100, choices=TEMPLATE_TYPES_CHOICES)
    message_template_id = models.CharField(max_length=20, unique=True, null=True, blank=True)

    def verify_namespace():
        pass

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        if not self.name:
            return

        if bool(re.match(r"\w*[A-Z]\w*", self.name)) or " " in self.name:
            message = _(
                """
                    Invalid name format.
                    The name must not contain spaces and must start with a lowercase letter
                    followed by one or more uppercase or lowercase letters,
                    digits, or underscores.
                """
            )
            error_message = textwrap.dedent(str(message))
            raise ValidationError({"name": error_message})


class TemplateTranslation(models.Model):
    STATUS_CHOICES = (
        ("APPROVED", "WhatsApp.data.templates.translaction.status.approved"),
        ("IN_APPEAL", "WhatsApp.data.templates.translaction.status.in_appeal"),
        ("PENDING", "WhatsApp.data.templates.translaction.status.pending"),
        ("REJECTED", "WhatsApp.data.templates.translaction.status.rejected"),
        (
            "PENDING_DELETION",
            "WhatsApp.data.templates.translaction.status.pending_deletion",
        ),
        ("DELETED", "WhatsApp.data.templates.translaction.status.deleted"),
        ("DISABLED", "WhatsApp.data.templates.translaction.status.disabled"),
        ("LOCKED", "WhatsApp.data.templates.translaction.status.locked"),
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    template = models.ForeignKey(
        TemplateMessage, on_delete=models.CASCADE, related_name="translations"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, null=True)

    body = models.CharField(max_length=2048, null=True)
    footer = models.CharField(max_length=60, null=True)
    variable_count = models.IntegerField(null=True)
    language = models.CharField(max_length=60, null=True)
    country = models.CharField(max_length=60, null=True)
    namespace = models.CharField(max_length=60, null=True)
    external_id = models.CharField(max_length=60, null=True)


class TemplateButton(models.Model):
    BUTTON_TYPE_CHOICES = (
        ("QUICK_REPLY", "WhatsApp.data.templates.buttons.type.quick_reply"),
        ("PHONE_NUMBER", "WhatsApp.data.templates.buttons.type.phone_number"),
        ("URL", "WhatsApp.data.templates.buttons.type.url"),
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    translation = models.ForeignKey(
        TemplateTranslation, on_delete=models.CASCADE, related_name="buttons"
    )

    button_type = models.CharField(max_length=20, choices=BUTTON_TYPE_CHOICES)
    text = models.CharField(max_length=30, null=True)
    country_code = models.IntegerField(null=True)
    phone_number = models.CharField(max_length=20, null=True)
    url = models.CharField(max_length=2000, null=True)


class TemplateHeader(models.Model):
    HEADER_TYPE_CHOICES = (
        ("TEXT", "WhatsApp.data.templates.header.types.text"),
        ("IMAGE", "WhatsApp.data.templates.header.types.image"),
        ("DOCUMENT", "WhatsApp.data.templates.header.types.document"),
        ("VIDEO", "WhatsApp.data.templates.header.types.video"),
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    translation = models.ForeignKey(
        TemplateTranslation, on_delete=models.CASCADE, related_name="headers"
    )
    header_type = models.CharField(max_length=20, choices=HEADER_TYPE_CHOICES)
    text = models.CharField(max_length=60, default=None, null=True)
    example = models.CharField(max_length=2048, default=None, null=True)

    def to_dict(self):
        return dict(header_type=self.header_type, text=self.text)
