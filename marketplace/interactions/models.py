from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator

from marketplace.core.models import AbstractBaseModel


class Rating(AbstractBaseModel):

    rate = models.IntegerField(validators=[MaxValueValidator(5), MinValueValidator(1)])
    app_slug = models.SlugField()

    class Meta:
        verbose_name = "Rating"
        verbose_name_plural = "Ratings"

    def __str__(self) -> str:
        return f"{self.rate} - {self.created_by.email}"


class Comment(AbstractBaseModel):

    content = models.TextField()
    app_slug = models.SlugField()

    class Meta:
        verbose_name = "Comment"
        verbose_name_plural = "Comments"

    def __str__(self) -> str:
        return self.content
