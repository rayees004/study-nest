from pathlib import Path

from django import forms
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from material_provider.models import (
    MaterialProviderProfile,
    Purchase,
    StudyMaterial,
)


class StudyNestUserCreationForm(UserCreationForm):
    user_type = forms.ChoiceField(
        label="I want to join as",
        choices=MaterialProviderProfile.USER_TYPES,
        initial="student",
        required=False,
    )

    class Meta(UserCreationForm.Meta):
        fields = ("username",)

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            MaterialProviderProfile.objects.create(
                user=user,
                user_type=self.cleaned_data.get("user_type") or "student",
            )
        return user


class StudyNestLoginView(LoginView):
    def get_success_url(self):
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to
        profile = getattr(self.request.user, "provider_profile", None)
        if profile and profile.user_type == "material_provider":
            return reverse("material_provider:dashboard")
        return reverse("public:catalog")


def material_catalog(request):
    collection = request.GET.get("collection", "available")
    if collection not in {"available", "purchased"}:
        collection = "available"

    materials = StudyMaterial.objects.filter(is_published=True)
    purchased_ids = set()
    if request.user.is_authenticated:
        purchased_ids = set(
            Purchase.objects.filter(student=request.user).values_list(
                "material_id", flat=True
            )
        )

    if collection == "purchased":
        materials = materials.filter(pk__in=purchased_ids)
    else:
        materials = materials.exclude(pk__in=purchased_ids)

    query = request.GET.get("q", "").strip()
    subject = request.GET.get("subject", "").strip()
    class_level = request.GET.get("class_level", "").strip()
    if query:
        materials = materials.filter(
            Q(title__icontains=query) | Q(subject__icontains=query)
        )
    if subject:
        materials = materials.filter(subject=subject)
    if class_level:
        materials = materials.filter(class_level=class_level)

    subjects = (
        StudyMaterial.objects.filter(is_published=True)
        .order_by("subject")
        .values_list("subject", flat=True)
        .distinct()
    )
    return render(
        request,
        "public/catalog.html",
        {
            "materials": materials,
            "collection": collection,
            "purchased_ids": purchased_ids,
            "query": query,
            "selected_subject": subject,
            "selected_class": class_level,
            "subjects": subjects,
            "class_levels": StudyMaterial.CLASS_LEVELS,
        },
    )


def material_detail(request, material_id):
    material = get_object_or_404(
        StudyMaterial, pk=material_id, is_published=True
    )
    purchased = request.user.is_authenticated and Purchase.objects.filter(
        student=request.user, material=material
    ).exists()
    return render(
        request,
        "public/material_detail.html",
        {"material": material, "purchased": purchased},
    )


@login_required
@require_POST
def purchase_material(request, material_id):
    material = get_object_or_404(
        StudyMaterial, pk=material_id, is_published=True
    )
    _, created = Purchase.objects.get_or_create(
        student=request.user,
        material=material,
        defaults={"price_at_purchase": material.price},
    )
    if created:
        messages.success(
            request,
            "Demo purchase complete. No payment was charged.",
        )
    else:
        messages.info(request, "This note is already in your library.")
    return redirect("public:library")


@login_required
def student_library(request):
    purchases = (
        Purchase.objects.filter(student=request.user, material__is_published=True)
        .select_related("material")
    )
    return render(request, "public/library.html", {"purchases": purchases})


@login_required
def download_material(request, material_id):
    material = get_object_or_404(
        StudyMaterial, pk=material_id, is_published=True
    )
    has_purchase = Purchase.objects.filter(
        student=request.user, material=material
    ).exists()
    if not has_purchase or not material.notes_file:
        raise Http404("Study notes are not available.")
    return FileResponse(
        material.notes_file.open("rb"),
        as_attachment=True,
        filename=Path(material.notes_file.name).name,
    )


def register_student(request):
    if request.user.is_authenticated:
        if getattr(request.user, "provider_profile", None) and (
            request.user.provider_profile.user_type == "material_provider"
        ):
            return redirect("material_provider:dashboard")
        return redirect("public:catalog")

    form = StudyNestUserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        if form.cleaned_data.get("user_type") == "material_provider":
            messages.success(request, "Your material provider account is ready.")
            return redirect("material_provider:dashboard")
        messages.success(request, "Your student account is ready.")
        return redirect("public:catalog")
    return render(request, "public/register.html", {"form": form})
