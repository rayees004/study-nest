from django.urls import path

from . import views

app_name = "material_provider"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("materials/add/", views.add_material, name="add_material"),
]
