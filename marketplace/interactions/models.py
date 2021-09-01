from django.db import models
from django.db.models import Avg
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models.constraints import UniqueConstraint

from marketplace.core.models import AppTypeBaseModel


class Rating(AppTypeBaseModel):

    rate = models.IntegerField(validators=[MaxValueValidator(5), MinValueValidator(1)])

    class Meta:
        verbose_name = "Rating"
        verbose_name_plural = "Ratings"
        constraints = [UniqueConstraint(fields=["created_by", "code"], name="unique_rationg_created_by_code")]

    def __str__(self) -> str:
        return f"{self.rate} - {self.created_by.email}"

    @classmethod
    def get_apptype_average(cls, code: str) -> float:
        return cls.objects.filter(code=code).aggregate(Avg("rate")).get("rate__avg")


class Comment(AppTypeBaseModel):

    content = models.TextField()

    class Meta:
        verbose_name = "Comment"
        verbose_name_plural = "Comments"

    def __str__(self) -> str:
        return self.content
