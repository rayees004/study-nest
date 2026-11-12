from datetime import timedelta
from decimal import Decimal
from functools import wraps

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncWeek
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import Purchase, StudyMaterial


class StudyMaterialForm(forms.ModelForm):
    class Meta:
        model = StudyMaterial
        fields = (
            "title",
            "subject",
            "class_level",
            "description",
            "price",
            "cover_image",
            "notes_content",
            "notes_file",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "notes_content": forms.Textarea(attrs={"rows": 6}),
        }


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
def add_material(request):
    form = StudyMaterialForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        material = form.save(commit=False)
        material.provider = request.user
        material.save()
        messages.success(request, "Your study material has been added.")
        return redirect("material_provider:dashboard")
    return render(
        request,
        "material_provider/add_material.html",
        {"form": form},
    )
