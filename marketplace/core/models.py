import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _


class AbstractBaseModel(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    criado_on = models.DateTimeField(_("Criado em"), editable=False, auto_now_add=True)
    modified_on = models.DateTimeField(_("Modificado em"), auto_now=True)

    class Meta:
        abstract = True
