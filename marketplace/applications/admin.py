from django.contrib import admin

from marketplace.applications.models import AppTypeAsset, AppTypeFeatured


# TODO: Create link choice that togle enter attachment and url

admin.site.register(AppTypeAsset)
admin.site.register(AppTypeFeatured)
