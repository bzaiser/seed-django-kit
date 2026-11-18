from django.core.management.base import BaseCommand

from seed_kit.registry import run_seeders


class Command(BaseCommand):
    help = "Führt registrierte Demo-Seeder (<app>/seeders.py) aus."

    def add_arguments(self, parser):
        parser.add_argument("--only", nargs="*", help="Nur bestimmte Seeder-Namen ausführen.")
        parser.add_argument("--count", type=int, default=10, help="Anzahl Datensätze pro Seeder.")
        parser.add_argument("--reset", action="store_true", help="Vorhandene Demo-Daten vorher zurücksetzen.")
        parser.add_argument("--dry-run", action="store_true", help="Transaktion am Ende zurückrollen.")

    def handle(self, *args, **options):
        results = run_seeders(
            only=options.get("only"),
            count=options["count"],
            reset=bool(options.get("reset")),
            dry_run=bool(options.get("dry_run")),
        )
        if not results:
            self.stdout.write(self.style.WARNING("Keine Seeder gefunden."))
            return
        for name, res in results:
            self.stdout.write(self.style.SUCCESS(f"Seeder '{name}' ausgeführt: {res}"))
        if options.get("dry_run"):
            self.stdout.write(self.style.WARNING("Dry-Run: Alle Änderungen wurden zurückgerollt."))
