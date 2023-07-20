from django.contrib import admin
from django.db.models import Max

from marketplace.applications.models import AppTypeAsset, AppTypeFeatured


# TODO: Create link choice that togle enter attachment and url


class AppTypeFeaturedAdmin(admin.ModelAdmin):
    fields = ["code", "priority"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            obj.modified_by = request.user

        else:
            obj.modified_by = request.user

        if not obj.priority:
            max_priority = AppTypeFeatured.objects.aggregate(Max("priority"))[
                "priority__max"
            ]
            obj.priority = max_priority + 1 if max_priority is not None else 1

        super().save_model(request, obj, form, change)


class AppTypeAssetAdmin(admin.ModelAdmin):
    exclude = ["created_by", "modified_by"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            obj.modified_by = request.user

        else:
            obj.modified_by = request.user

        super().save_model(request, obj, form, change)


admin.site.register(AppTypeAsset, AppTypeAssetAdmin)
admin.site.register(AppTypeFeatured, AppTypeFeaturedAdmin)
