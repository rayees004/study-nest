from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from .models import MaterialProviderProfile, Purchase, StudyMaterial


class StudentMaterialTests(TestCase):
    def setUp(self):
        self.material = StudyMaterial.objects.create(
            title="Algebra essentials",
            subject="Mathematics",
            class_level="Class 10",
            description="A clear guide to quadratic equations.",
            price=Decimal("149.00"),
            notes_content="The quadratic formula is x = (-b ± √(b² - 4ac)) / 2a.",
        )
        self.user = get_user_model().objects.create_user(
            username="student",
            password="a-safe-test-password",
        )

    def test_catalog_is_public_and_shows_note_and_price(self):
        response = self.client.get(reverse("public:catalog"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Algebra essentials")
        self.assertContains(response, "₹149")

    def test_catalog_filters_by_subject_class_and_search(self):
        response = self.client.get(
            reverse("public:catalog"),
            {"q": "algebra", "subject": "Mathematics", "class_level": "Class 10"},
        )

        self.assertContains(response, "Algebra essentials")
        self.assertEqual(len(response.context["materials"]), 1)

    def test_public_can_preview_but_not_read_notes_before_purchase(self):
        response = self.client.get(
            reverse("public:detail", args=[self.material.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "quadratic formula is")
        self.assertContains(response, "₹149")

    def test_purchase_requires_login(self):
        response = self.client.post(
            reverse("public:purchase", args=[self.material.pk])
        )

        self.assertRedirects(
            response,
            f"{reverse('public:login')}?next={reverse('public:purchase', args=[self.material.pk])}",
        )
        self.assertEqual(Purchase.objects.count(), 0)

    def test_student_can_purchase_once_and_read_owned_notes(self):
        self.client.force_login(self.user)
        purchase_url = reverse("public:purchase", args=[self.material.pk])
        response = self.client.post(purchase_url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], reverse("public:library"))
        self.assertContains(response, "No payment was charged")
        self.assertEqual(Purchase.objects.count(), 1)
        self.assertEqual(
            Purchase.objects.get().price_at_purchase,
            Decimal("149.00"),
        )

        response = self.client.get(
            reverse("public:detail", args=[self.material.pk])
        )
        self.assertContains(response, "quadratic formula is")

        self.client.post(purchase_url)
        self.assertEqual(Purchase.objects.count(), 1)

    def test_offer_price_is_shown_and_saved_when_material_is_purchased(self):
        self.material.offer_percentage = 20
        self.material.save(update_fields=["offer_percentage"])
        self.client.force_login(self.user)

        catalog = self.client.get(reverse("public:catalog"))
        self.assertContains(catalog, "20% OFF")
        self.assertContains(catalog, "₹119")

        self.client.post(reverse("public:purchase", args=[self.material.pk]))
        purchase = Purchase.objects.get(student=self.user, material=self.material)
        self.assertEqual(purchase.price_at_purchase, Decimal("119.20"))

    def test_catalog_separates_purchased_notes_from_available_notes(self):
        Purchase.objects.create(
            student=self.user,
            material=self.material,
            price_at_purchase=self.material.price,
        )
        self.client.force_login(self.user)

        available = self.client.get(reverse("public:catalog"))
        purchased = self.client.get(
            reverse("public:catalog"), {"collection": "purchased"}
        )

        self.assertNotContains(available, "Algebra essentials")
        self.assertContains(purchased, "Algebra essentials")

    def test_uploaded_notes_can_only_be_downloaded_by_a_buyer(self):
        self.material.notes_file.save(
            "algebra.txt",
            SimpleUploadedFile("algebra.txt", b"Class notes"),
        )
        download_url = reverse("public:download", args=[self.material.pk])

        self.client.force_login(self.user)
        self.assertEqual(self.client.get(download_url).status_code, 404)

        Purchase.objects.create(
            student=self.user,
            material=self.material,
            price_at_purchase=self.material.price,
        )
        response = self.client.get(download_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"Class notes")

    def test_student_can_create_an_account(self):
        response = self.client.post(
            reverse("public:register"),
            {
                "username": "newstudent",
                "password1": "a-very-safe-test-password",
                "password2": "a-very-safe-test-password",
            },
        )

        self.assertRedirects(response, reverse("public:catalog"))
        self.assertTrue(
            get_user_model().objects.filter(username="newstudent").exists()
        )
        self.assertEqual(
            MaterialProviderProfile.objects.get(
                user__username="newstudent"
            ).user_type,
            "student",
        )

    def test_material_provider_can_register_and_use_the_shared_login(self):
        registration = self.client.post(
            reverse("public:register"),
            {
                "username": "provider",
                "password1": "a-very-safe-test-password",
                "password2": "a-very-safe-test-password",
                "user_type": "material_provider",
            },
        )

        self.assertRedirects(
            registration,
            reverse("material_provider:dashboard"),
        )
        self.client.post(reverse("public:logout"))
        login_response = self.client.post(
            reverse("public:login"),
            {
                "username": "provider",
                "password": "a-very-safe-test-password",
            },
        )

        self.assertRedirects(
            login_response,
            reverse("material_provider:dashboard"),
        )


class MaterialProviderDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="provider",
            password="a-safe-test-password",
        )
        MaterialProviderProfile.objects.create(
            user=self.user,
            user_type="material_provider",
        )
        self.material = StudyMaterial.objects.create(
            title="Biology notes",
            subject="Biology",
            class_level="Class 9",
            description="Cell structure notes",
            price="100.00",
            provider=self.user,
        )
        self.student = get_user_model().objects.create_user(
            username="buyer",
            password="a-safe-test-password",
        )
        Purchase.objects.create(
            student=self.student,
            material=self.material,
            price_at_purchase="100.00",
        )
        self.client.force_login(self.user)

    def test_dashboard_shows_provider_metrics(self):
        response = self.client.get(reverse("material_provider:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["materials_count"], 1)
        self.assertEqual(response.context["earnings"], 100)
        self.assertEqual(response.context["orders_count"], 1)
        self.assertEqual(response.context["students_count"], 1)
        self.assertContains(response, "Biology notes")

    def test_materials_page_lists_only_provider_materials_with_category(self):
        another_provider = get_user_model().objects.create_user(
            username="another-provider",
            password="a-safe-test-password",
        )
        StudyMaterial.objects.create(
            title="Private notes",
            subject="History",
            class_level="Class 8",
            description="Not this provider's material",
            price="50.00",
            provider=another_provider,
        )

        dashboard = self.client.get(reverse("material_provider:dashboard"))
        response = self.client.get(reverse("material_provider:materials"))

        self.assertContains(
            dashboard,
            reverse("material_provider:materials"),
        )
        self.assertContains(response, "Uploaded Materials")
        self.assertContains(response, "Biology notes")
        self.assertContains(response, "Biology")
        self.assertContains(response, "Add material")
        self.assertNotContains(response, "0% OFF")
        self.assertNotContains(response, "Private notes")

    def test_add_material_form_uses_material_name_and_category_labels(self):
        response = self.client.get(reverse("material_provider:add_material"))

        self.assertContains(response, "Material name")
        self.assertContains(response, "Category")
        self.assertContains(response, "Add a new category")

    def test_provider_can_add_material_to_their_account(self):
        response = self.client.post(
            reverse("material_provider:add_material"),
            {
                "title": "Chemistry guide",
                "subject": "Chemistry",
                "class_level": "Class 10",
                "description": "Reactions and equations",
                "price": "120.00",
                "subject": "__new__",
                "new_subject": "Chemistry",
                "notes_content": "Study notes",
                "offer_percentage": "15",
            },
        )

        self.assertRedirects(
            response,
            reverse("material_provider:materials"),
        )
        material = StudyMaterial.objects.get(title="Chemistry guide")
        self.assertEqual(material.provider, self.user)
        self.assertEqual(material.subject, "Chemistry")
        self.assertEqual(material.offer_percentage, 15)
        self.assertTrue(material.is_published)

    def test_provider_can_upload_cover_and_optional_explanation_video(self):
        image_data = BytesIO()
        Image.new("RGB", (2, 2), color="green").save(
            image_data,
            format="PNG",
        )
        response = self.client.post(
            reverse("material_provider:add_material"),
            {
                "title": "Visual science guide",
                "subject": "__new__",
                "new_subject": "Science",
                "class_level": "Class 8",
                "description": "An illustrated science guide",
                "price": "75.00",
                "offer_percentage": "0",
                "cover_image_file": SimpleUploadedFile(
                    "cover.png",
                    image_data.getvalue(),
                    content_type="image/png",
                ),
                "explanation_video": SimpleUploadedFile(
                    "explanation.mp4",
                    b"video content",
                    content_type="video/mp4",
                ),
            },
        )

        self.assertRedirects(
            response,
            reverse("material_provider:materials"),
        )
        material = StudyMaterial.objects.get(title="Visual science guide")
        try:
            self.assertTrue(material.cover_image_file.name.endswith("cover.png"))
            self.assertTrue(
                material.explanation_video.name.endswith("explanation.mp4")
            )
            provider_page = self.client.get(
                reverse("material_provider:materials")
            )
            self.assertContains(provider_page, material.cover_image_file.url)
            catalog_page = self.client.get(reverse("public:catalog"))
            self.assertContains(catalog_page, material.cover_image_file.url)
            detail_page = self.client.get(
                reverse("public:detail", args=[material.pk])
            )
            self.assertContains(detail_page, material.cover_image_file.url)
            self.assertNotContains(detail_page, "cover-placeholder")
        finally:
            material.cover_image_file.delete(save=False)
            material.explanation_video.delete(save=False)

    def test_provider_can_edit_material_and_publish_status(self):
        edit_response = self.client.post(
            reverse("material_provider:edit_material", args=[self.material.pk]),
            {
                "title": "Updated biology notes",
                "subject": "Biology",
                "class_level": "Class 9",
                "description": "Updated description",
                "price": "120.00",
                "notes_content": "Updated notes",
                "offer_percentage": "10",
            },
        )

        self.assertRedirects(
            edit_response,
            reverse("material_provider:materials"),
        )
        self.material.refresh_from_db()
        self.assertEqual(self.material.title, "Updated biology notes")
        self.assertEqual(self.material.offer_percentage, 10)

        toggle_url = reverse(
            "material_provider:toggle_material_published",
            args=[self.material.pk],
        )
        self.client.post(toggle_url)
        self.material.refresh_from_db()
        self.assertFalse(self.material.is_published)
        self.client.post(toggle_url)
        self.material.refresh_from_db()
        self.assertTrue(self.material.is_published)

    def test_material_list_filters_by_category_and_status(self):
        unpublished = StudyMaterial.objects.create(
            title="Unpublished biology",
            subject="Biology",
            class_level="Class 8",
            description="Not visible in the published filter",
            price="50.00",
            provider=self.user,
            is_published=False,
        )
        StudyMaterial.objects.create(
            title="History notes",
            subject="History",
            class_level="Class 8",
            description="Another subject",
            price="50.00",
            provider=self.user,
        )

        response = self.client.get(
            reverse("material_provider:materials"),
            {"category": "Biology", "status": "published"},
        )

        self.assertContains(response, self.material.title)
        self.assertNotContains(response, unpublished.title)
        self.assertNotContains(response, "History notes")

    def test_provider_cannot_edit_or_toggle_another_providers_material(self):
        another_provider = get_user_model().objects.create_user(
            username="another-material-provider",
            password="a-safe-test-password",
        )
        other_material = StudyMaterial.objects.create(
            title="Other provider material",
            subject="Science",
            class_level="Class 8",
            description="Owned by another provider",
            price="50.00",
            provider=another_provider,
        )

        edit_response = self.client.get(
            reverse("material_provider:edit_material", args=[other_material.pk])
        )
        toggle_response = self.client.post(
            reverse(
                "material_provider:toggle_material_published",
                args=[other_material.pk],
            )
        )

        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(toggle_response.status_code, 404)

    def test_student_cannot_open_provider_dashboard(self):
        student = get_user_model().objects.create_user(
            username="another-student",
            password="a-safe-test-password",
        )
        MaterialProviderProfile.objects.create(
            user=student,
            user_type="student",
        )
        self.client.force_login(student)

        response = self.client.get(reverse("material_provider:dashboard"))

        self.assertRedirects(response, reverse("public:catalog"))
