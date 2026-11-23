from datetime import timedelta
from decimal import Decimal
from functools import wraps

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncWeek
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Purchase, StudyMaterial


class StudyMaterialForm(forms.ModelForm):
    subject = forms.ChoiceField(
        label="Category",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_subject"}),
    )
    new_subject = forms.CharField(
        label="New category name",
        max_length=80,
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter category name (e.g. Science, Mathematics)",
                "class": "form-input",
                "id": "id_new_subject",
            }
        ),
    )
    class_level = forms.ChoiceField(
        label="Class",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_class_level"}),
    )

    class Meta:
        model = StudyMaterial
        fields = (
            "title",
            "subject",
            "class_level",
            "description",
            "price",
            "cover_image_file",
            "notes_content",
            "notes_file",
            "explanation_video",
            "offer_percentage",
        )
        labels = {
            "title": "Material name",
            "class_level": "Class",
            "description": "Description",
            "price": "Amount",
            "cover_image_file": "Cover picture",
            "notes_content": "Material explanation",
            "notes_file": "Study material file",
            "explanation_video": "Explanation video (optional)",
            "offer_percentage": "Offer rate (%)",
        }
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "e.g., Complete Class 10 Physics Mechanics Notes",
                    "class": "form-input",
                    "id": "id_title",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Brief summary of what this study material covers (visible to students on cards)...",
                    "class": "form-textarea",
                    "id": "id_description",
                }
            ),
            "notes_content": forms.Textarea(
                attrs={
                    "rows": 6,
                    "placeholder": "Write or paste the full study notes, key formulas, summary, and explanations here...",
                    "class": "form-textarea",
                    "id": "id_notes_content",
                }
            ),
            "price": forms.NumberInput(
                attrs={
                    "min": "0",
                    "step": "1",
                    "placeholder": "0",
                    "class": "form-input",
                    "id": "id_price",
                }
            ),
            "offer_percentage": forms.NumberInput(
                attrs={
                    "min": 0,
                    "max": 100,
                    "placeholder": "0",
                    "class": "form-input",
                    "id": "id_offer_percentage",
                }
            ),
            "cover_image_file": forms.ClearableFileInput(
                attrs={"accept": "image/*", "class": "file-input-hidden", "id": "id_cover_image_file"}
            ),
            "notes_file": forms.ClearableFileInput(
                attrs={"accept": ".pdf,.doc,.docx,.txt,.zip", "class": "file-input-hidden", "id": "id_notes_file"}
            ),
            "explanation_video": forms.ClearableFileInput(
                attrs={"accept": "video/*", "class": "file-input-hidden", "id": "id_explanation_video"}
            ),
        }

    def __init__(self, *args, provider=None, **kwargs):
        super().__init__(*args, **kwargs)
        categories = []
        if provider is not None:
            categories = list(
                StudyMaterial.objects.filter(provider=provider)
                .order_by("subject")
                .values_list("subject", flat=True)
                .distinct()
            )
        current_category = self.instance.subject if self.instance.pk else ""
        if current_category and current_category not in categories:
            categories.append(current_category)
        self.fields["subject"].choices = [
            ("", "Select a category"),
            *((category, category) for category in categories),
            ("__new__", "Add a new category"),
        ]

        current_class = self.instance.class_level if self.instance.pk else ""
        classes = [c for c, _ in StudyMaterial.CLASS_LEVELS]
        if current_class and current_class not in classes:
            classes.append(current_class)
        posted_class = self.data.get("class_level") if self.data else None
        if posted_class and posted_class not in classes:
            classes.append(posted_class)
        self.fields["class_level"].choices = [
            ("", "Select target class"),
            *((c, c) for c in classes),
        ]

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("subject")
        new_category = cleaned_data.get("new_subject", "").strip()
        if category == "__new__":
            if not new_category:
                self.add_error("new_subject", "Enter a name for the new category.")
            else:
                cleaned_data["subject"] = new_category
        elif new_category:
            self.add_error(
                "new_subject",
                "Choose 'Add a new category' to use this field.",
            )
        return cleaned_data


def material_provider_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        profile = getattr(request.user, "provider_profile", None)
        if not profile or profile.user_type != "material_provider":
            messages.error(request, "A material provider account is required.")
            return redirect("public:catalog")
        return view(request, *args, **kwargs)

    return wrapped


@material_provider_required
def dashboard(request):
    materials = StudyMaterial.objects.filter(provider=request.user)
    query = request.GET.get("q", "").strip()
    matching_materials = materials
    if query:
        matching_materials = materials.filter(
            Q(title__icontains=query) | Q(subject__icontains=query)
        )
    purchases = Purchase.objects.filter(
        material__provider=request.user
    ).select_related("student", "material")
    totals = purchases.aggregate(
        earnings=Sum("price_at_purchase"),
        orders=Count("pk"),
        students=Count("student", distinct=True),
    )

    today = timezone.localdate()
    current_week = today - timedelta(days=today.weekday())
    week_starts = [
        current_week - timedelta(weeks=offset)
        for offset in range(3, -1, -1)
    ]
    weekly_revenue = {}
    for row in (
        purchases.filter(purchased_at__date__gte=week_starts[0])
        .annotate(week=TruncWeek("purchased_at"))
        .values("week")
        .annotate(revenue=Sum("price_at_purchase"))
    ):
        week = row["week"]
        if hasattr(week, "date"):
            week = week.date()
        weekly_revenue[week] = row["revenue"] or Decimal("0")

    sales_weeks = [
        {
            "label": f"Week {index + 1}",
            "revenue": weekly_revenue.get(week, Decimal("0")),
        }
        for index, week in enumerate(week_starts)
    ]
    max_revenue = max(
        (week["revenue"] for week in sales_weeks),
        default=Decimal("0"),
    ) or Decimal("1")
    chart_points = []
    for index, week in enumerate(sales_weeks):
        chart_points.append(
            {
                **week,
                "x": 30 + index * 155,
                "y": 128 - float(week["revenue"] / max_revenue) * 92,
            }
        )
    chart_path = " ".join(
        ("M" if index == 0 else "L")
        + f' {point["x"]} {point["y"]:.1f}'
        for index, point in enumerate(chart_points)
    )

    top_materials = list(
        matching_materials.annotate(sales=Count("purchases"))
        .order_by("-sales", "title")[:3]
    )
    max_sales = max((material.sales for material in top_materials), default=0)
    for material in top_materials:
        material.sales_percent = (
            round(material.sales * 100 / max_sales) if max_sales else 0
        )
    chart_area_path = (
        f"{chart_path} L {chart_points[-1]['x']} 128 "
        f"L {chart_points[0]['x']} 128 Z"
    )
    context = {
        "materials_count": materials.count(),
        "earnings": totals["earnings"] or Decimal("0"),
        "orders_count": totals["orders"],
        "students_count": totals["students"],
        "recent_purchases": purchases.order_by("-purchased_at")[:5],
        "top_materials": top_materials,
        "sales_weeks": chart_points,
        "chart_path": chart_path,
        "chart_area_path": chart_area_path,
        "chart_max_revenue": max_revenue,
        "provider_name": request.user.get_full_name() or request.user.username,
        "date_range": f"{today.strftime('%b')} 1 – {today.strftime('%b %d, %Y')}",
        "search_query": query,
    }
    return render(request, "material_provider/dashboard.html", context)


@material_provider_required
def materials(request):
    provider_materials = StudyMaterial.objects.filter(provider=request.user)
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    status = request.GET.get("status", "").strip()
    if query:
        provider_materials = provider_materials.filter(
            Q(title__icontains=query)
            | Q(subject__icontains=query)
            | Q(description__icontains=query)
        )
    if category:
        provider_materials = provider_materials.filter(subject=category)
    if status == "published":
        provider_materials = provider_materials.filter(is_published=True)
    elif status == "unpublished":
        provider_materials = provider_materials.filter(is_published=False)
    return render(
        request,
        "material_provider/materials.html",
        {
            "provider_materials": provider_materials.order_by("-created_at"),
            "materials_count": StudyMaterial.objects.filter(provider=request.user).count(),
            "categories": (
                StudyMaterial.objects.filter(provider=request.user)
                .order_by("subject")
                .values_list("subject", flat=True)
                .distinct()
            ),
            "selected_category": category,
            "selected_status": status,
            "provider_name": request.user.get_full_name() or request.user.username,
            "search_query": query,
        },
    )


@material_provider_required
def add_material(request):
    form = StudyMaterialForm(
        request.POST or None,
        request.FILES or None,
        provider=request.user,
    )
    if request.method == "POST" and form.is_valid():
        material = form.save(commit=False)
        material.provider = request.user
        material.save()
        messages.success(request, "Your study material has been added.")
        return redirect("material_provider:materials")
    return render(
        request,
        "material_provider/add_material.html",
        {"form": form, "is_edit": False},
    )


@material_provider_required
def edit_material(request, material_id):
    material = get_object_or_404(
        StudyMaterial,
        pk=material_id,
        provider=request.user,
    )
    form = StudyMaterialForm(
        request.POST or None,
        request.FILES or None,
        instance=material,
        provider=request.user,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your study material has been updated.")
        return redirect("material_provider:materials")
    return render(
        request,
        "material_provider/add_material.html",
        {"form": form, "is_edit": True, "material": material},
    )


@material_provider_required
@require_POST
def toggle_material_published(request, material_id):
    material = get_object_or_404(
        StudyMaterial,
        pk=material_id,
        provider=request.user,
    )
    material.is_published = not material.is_published
    material.save(update_fields=["is_published"])
    status = "published" if material.is_published else "unpublished"
    messages.success(request, f"Your study material is now {status}.")
    return redirect("material_provider:materials")
