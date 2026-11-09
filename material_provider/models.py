from django.conf import settings
from django.db import models


class StudyMaterial(models.Model):
    CLASS_LEVELS = [
        ("Class 6", "Class 6"),
        ("Class 7", "Class 7"),
        ("Class 8", "Class 8"),
        ("Class 9", "Class 9"),
        ("Class 10", "Class 10"),
        ("Class 11", "Class 11"),
        ("Class 12", "Class 12"),
    ]

    title = models.CharField(max_length=180)
    subject = models.CharField(max_length=80)
    class_level = models.CharField(max_length=20, choices=CLASS_LEVELS)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    cover_image = models.URLField(blank=True)
    notes_content = models.TextField(blank=True)
    notes_file = models.FileField(upload_to="study_notes/", blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["subject", "class_level", "title"]

    def __str__(self):
        return f"{self.title} · {self.class_level}"


class Purchase(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_note_purchases",
    )
    material = models.ForeignKey(
        StudyMaterial,
        on_delete=models.CASCADE,
        related_name="purchases",
    )
    price_at_purchase = models.DecimalField(max_digits=8, decimal_places=2)
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-purchased_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "material"],
                name="unique_student_material_purchase",
            )
        ]

    def __str__(self):
        return f"{self.student} · {self.material}"
