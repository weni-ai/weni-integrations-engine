import uuid

from django.db import models
from django.db.models.fields import URLField
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.models import UserManager as BaseUserManager

from marketplace.core.models import BaseModel


class UserManager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if not email:
            raise ValueError("The given email must be set")

        email = self.normalize_email(email)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):

    first_name = models.CharField(_("first name"), max_length=30, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    email = models.EmailField(_("email"), unique=True, help_text=_("User email"))

    photo_url = URLField(blank=True, max_length=255)

    is_staff = models.BooleanField(_("staff status"), default=False)
    is_active = models.BooleanField(_("active"), default=True)

    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    objects = UserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")


class ProjectAuthorization(models.Model):

    ROLE_NOT_SETTED = 0
    ROLE_VIEWER = 1
    ROLE_CONTRIBUTOR = 2
    ROLE_ADMIN = 3

    ROLE_CHOICES = (
        (ROLE_NOT_SETTED, "not set"),
        (ROLE_VIEWER, "viewer"),
        (ROLE_CONTRIBUTOR, "contributor"),
        (ROLE_ADMIN, "admin"),
    )

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, models.CASCADE, related_name="authorizations")
    project_uuid = models.UUIDField()

    role = models.PositiveIntegerField(choices=ROLE_CHOICES, default=ROLE_NOT_SETTED)

    created_on = models.DateTimeField("Created on", editable=False, auto_now_add=True)
    modified_on = models.DateTimeField("Modified on", auto_now=True)

    class Meta:
        verbose_name = "Project Authorization"
        verbose_name_plural = "Project Authorizations"
        unique_together = ["user", "project_uuid"]

    def __str__(self) -> str:
        return f"{self.user} - {self.project_uuid}"

    def set_role(self, role: int):
        assert role in dict(self.ROLE_CHOICES), f"Role: {role} isn't valid!"
        self.role = role
        self.save()

    def can_contribute(self, obj: BaseModel) -> bool:
        return obj.created_by == self.user and self.is_contributor

    def can_destroy(self, obj):
        return self.is_admin or self.can_contribute(obj)

    @property
    def can_write(self) -> bool:
        return self.is_contributor or self.is_admin

    @property
    def is_viewer(self):
        return self.role == self.ROLE_VIEWER

    @property
    def is_contributor(self):
        return self.role == self.ROLE_CONTRIBUTOR

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN
