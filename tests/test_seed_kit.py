import io
import os
import sys

import django
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY="test-seed-kit",
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.messages",
            "design_studio",
            "seed_kit",
        ],
        MIDDLEWARE=[
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
        ],
        ROOT_URLCONF="tests.test_seed_kit",
        TEMPLATES=[{
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "APP_DIRS": True,
            "OPTIONS": {"context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "design_studio.context_processors.theme_context",
            ]},
        }],
    )
    django.setup()

from django.urls import include, path
urlpatterns = [
    path("design-studio/", include("design_studio.urls")),
    path("setup/", include("seed_kit.urls")),
]

from django.contrib.auth import get_user_model
from seed_kit.registry import clear_seeders, fake_email, fake_name, register_seeder

User = get_user_model()


class SeedKitTests(TestCase):
    def tearDown(self):
        clear_seeders()

    def test_seed_demo_reset_count_and_dry_run(self):
        def reset_users():
            User.objects.all().delete()

        def seed_users(count=5):
            for i in range(count):
                User.objects.create_user(username=f"demo_{i}", password="pw")
            return count

        register_seeder("users", seed_users, order=1, reset_fn=reset_users)

        out = io.StringIO()
        call_command("seed_demo", count=3, dry_run=True, stdout=out)
        self.assertEqual(User.objects.count(), 0)
        self.assertIn("Dry-Run", out.getvalue())

        call_command("seed_demo", count=4, reset=True, stdout=io.StringIO())
        self.assertEqual(User.objects.count(), 4)
        self.assertTrue("@example.com" in fake_email(fake_name()))


    def test_setup_wizard_permissions_apply_and_dismiss(self):
        from seed_kit.models import SetupWizardState

        staff = User.objects.create_user(username="adm", password="pw", is_staff=True)
        member = User.objects.create_user(username="mem", password="pw", is_staff=False)

        self.client.force_login(member)
        r_mem = self.client.get("/setup/")
        self.assertNotEqual(r_mem.status_code, 200)

        self.client.force_login(staff)
        r_get = self.client.get("/setup/")
        self.assertEqual(r_get.status_code, 200)
        self.assertContains(r_get, "Ersteinrichtungs-Assistent")

        r_post = self.client.post("/setup/apply/", {
            "profile_key": "verein",
            "addons": ["academy", "membership", "newsletter"],
            "site_name": "TSV Test",
            "modules": ["persons", "documents"],
            "enable_website": "on",
            "blocks": ["hero"],
            "forms": ["kontakt-anfragen"],
            "groups": ["Redakteur"],
            "calendar_categories_text": "Veranstaltungen, Kurse",
            "hide_on_start": "on",
        })
        self.assertEqual(r_post.status_code, 302)
        state = SetupWizardState.get_solo()
        self.assertTrue(state.is_completed)
        self.assertTrue(state.hide_on_start)
        self.assertEqual(state.profile_key, "verein")

    def test_no_missing_migrations(self):
        call_command("makemigrations", "seed_kit", "--check", "--dry-run", verbosity=0)


if __name__ == "__main__":
    from django.test.runner import DiscoverRunner
    call_command("migrate", verbosity=0)
    runner = DiscoverRunner(verbosity=2)
    sys.exit(bool(runner.run_tests(["tests.test_seed_kit"])))
