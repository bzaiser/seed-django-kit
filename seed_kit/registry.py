from datetime import timedelta
from decimal import Decimal
import importlib
import random

from django.apps import apps
from django.db import transaction
from django.utils import timezone

_REGISTRY: dict[str, dict] = {}

FIRST_NAMES = ("Anna", "Bernd", "Clara", "David", "Elena", "Felix", "Greta", "Jonas", "Lea", "Max")
LAST_NAMES = ("Müller", "Schmidt", "Weber", "Meyer", "Wagner", "Becker", "Hoffmann", "Schäfer", "Koch", "Bauer")


def register_seeder(name: str, fn, order: int = 50, reset_fn=None):
    _REGISTRY[name] = {
        "name": name,
        "fn": fn,
        "order": order,
        "reset_fn": reset_fn,
    }


def clear_seeders():
    _REGISTRY.clear()


def discover_seeders():
    for app_config in apps.get_app_configs():
        mod_name = f"{app_config.name}.seeders"
        try:
            importlib.import_module(mod_name)
        except ModuleNotFoundError as exc:
            if exc.name != mod_name:
                raise


def run_seeders(only=None, count: int = 10, reset: bool = False, dry_run: bool = False):
    discover_seeders()
    selected = sorted(_REGISTRY.values(), key=lambda x: (x["order"], x["name"]))
    if only:
        only_set = set(only)
        selected = [s for s in selected if s["name"] in only_set]

    executed = []
    with transaction.atomic():
        if reset:
            for item in reversed(selected):
                if item["reset_fn"]:
                    item["reset_fn"]()
        for item in selected:
            res = item["fn"](count=count)
            executed.append((item["name"], res))
        if dry_run:
            transaction.set_rollback(True)
    return executed


def fake_name(rng: random.Random | None = None) -> str:
    r = rng or random
    return f"{r.choice(FIRST_NAMES)} {r.choice(LAST_NAMES)}"


def fake_email(name: str, domain: str = "example.com") -> str:
    clean = name.lower().replace(" ", ".").replace("ü", "ue").replace("ä", "ae").replace("ö", "oe")
    return f"{clean}@{domain}"


def fake_amount(min_val: float = 10.0, max_val: float = 500.0, rng: random.Random | None = None) -> Decimal:
    r = rng or random
    return Decimal(str(round(r.uniform(min_val, max_val), 2)))


def fake_date_offset(days_back: int = 30, days_forward: int = 30, rng: random.Random | None = None):
    r = rng or random
    return timezone.now() + timedelta(days=r.randint(-days_back, days_forward))
