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
            "seed_kit",
        ],
    )
    django.setup()

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


    def test_no_missing_migrations(self):
        call_command("makemigrations", "seed_kit", "--check", "--dry-run", verbosity=0)


if __name__ == "__main__":
    from django.test.runner import DiscoverRunner
    call_command("migrate", verbosity=0)
    runner = DiscoverRunner(verbosity=2)
    sys.exit(bool(runner.run_tests(["tests.test_seed_kit"])))
