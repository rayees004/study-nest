from pathlib import Path

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from material_provider.models import Purchase, StudyMaterial


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
        return redirect("public:catalog")

    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        student = form.save()
        login(request, student)
        messages.success(request, "Your student account is ready.")
        return redirect("public:catalog")
    return render(request, "public/register.html", {"form": form})
