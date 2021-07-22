from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models.constraints import UniqueConstraint

from marketplace.applications.models import AppBaseModel


class Rating(AppBaseModel):

    rate = models.IntegerField(validators=[MaxValueValidator(5), MinValueValidator(1)])

    class Meta:
        verbose_name = "Rating"
        verbose_name_plural = "Ratings"
        constraints = [UniqueConstraint(fields=["created_by", "app_code"], name="unique_rationg_created_by_app_code")]

    def __str__(self) -> str:
        return f"{self.rate} - {self.created_by.email}"


class Comment(AppBaseModel):

    content = models.TextField()

    class Meta:
        verbose_name = "Comment"
        verbose_name_plural = "Comments"

    def __str__(self) -> str:
        return self.content
