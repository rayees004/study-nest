from django.urls import path

from . import views

app_name = "material_provider"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("materials/", views.materials, name="materials"),
    path("materials/add/", views.add_material, name="add_material"),
    path("materials/<int:material_id>/edit/", views.edit_material, name="edit_material"),
    path(
        "materials/<int:material_id>/toggle-published/",
        views.toggle_material_published,
        name="toggle_material_published",
    ),
]
