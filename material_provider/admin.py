from django.contrib import admin

from .models import Purchase, StudyMaterial


@admin.register(StudyMaterial)
class StudyMaterialAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "class_level", "price", "is_published")
    list_filter = ("subject", "class_level", "is_published")
    search_fields = ("title", "subject", "description")
    list_editable = ("price", "is_published")


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("student", "material", "price_at_purchase", "purchased_at")
    list_filter = ("purchased_at",)
    search_fields = ("student__username", "material__title")
