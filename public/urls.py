from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "public"

urlpatterns = [
    path("", views.material_catalog, name="catalog"),
    path("library/", views.student_library, name="library"),
    path("materials/<int:material_id>/", views.material_detail, name="detail"),
    path(
        "materials/<int:material_id>/purchase/",
        views.purchase_material,
        name="purchase",
    ),
    path(
        "materials/<int:material_id>/download/",
        views.download_material,
        name="download",
    ),
    path(
        "accounts/login/",
        views.StudyNestLoginView.as_view(
            template_name="public/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path("accounts/register/", views.register_student, name="register"),
]
