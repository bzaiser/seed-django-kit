from django.apps import apps
from django.db import transaction
from django.utils import timezone

from .models import SetupWizardState
from .registry import run_seeders


WIZARD_PROFILES = {
    "verein": {
        "label": "Verein / Club",
        "icon": "bi-people-fill",
        "description": "Mitglieder, Vorstand, Beiträge/Konten, Kurse, Veranstaltungen & öffentliche Webseite.",
        "modules": ["master_data", "persons", "addresses", "inventory", "contracts", "accounts", "documents", "global_search"],
        "enable_website": True,
        "blocks": ["hero", "text_image", "news_feed", "upcoming_events", "people_grid", "downloads", "faq_list"],
        "forms": ["kontakt-anfragen", "kurs-anmeldung", "mitgliedsantrag", "kuendigung", "newsletter-abo"],
        "groups": ["Mitglied / Portal", "Redakteur", "Buchhaltung / Kassierer", "Leitung / Vorstand"],
        "calendar_categories": [
            {"name": "Veranstaltungen", "color_state": 1, "is_shared": True, "is_public_default": True},
            {"name": "Kurse", "color_state": 2, "is_shared": True, "is_public_default": True},
            {"name": "Vorstand / Intern", "color_state": 3, "is_shared": True, "is_public_default": False},
        ],
    },
    "company": {
        "label": "Unternehmen / Team",
        "icon": "bi-building",
        "description": "Mitarbeiter, Kunden/Kontakte, Verträge, Inventar, Räume & Dokumentenarchiv.",
        "modules": ["master_data", "persons", "addresses", "assets", "contracts", "inventory", "documents", "global_search"],
        "enable_website": True,
        "blocks": ["hero", "text_image", "news_feed", "people_grid", "downloads"],
        "forms": ["kontakt-anfragen", "newsletter-abo"],
        "groups": ["Redakteur", "Buchhaltung / Kassierer", "Mitarbeiter", "Leitung / Vorstand"],
        "calendar_categories": [
            {"name": "Team-Termine", "color_state": 1, "is_shared": True, "is_public_default": False},
            {"name": "Räume & Ressourcen", "color_state": 5, "is_shared": True, "is_public_default": False},
        ],
    },
    "academy": {
        "label": "Kursbetrieb / Akademie",
        "icon": "bi-mortarboard-fill",
        "description": "Dozenten mit Vita, Online-Kursanmeldung mit Teilnehmerlimit, Räume & öffentliche Termine.",
        "modules": ["master_data", "persons", "addresses", "inventory", "documents", "global_search"],
        "enable_website": True,
        "blocks": ["hero", "upcoming_events", "people_grid", "faq_list", "downloads"],
        "forms": ["kurs-anmeldung", "kontakt-anfragen", "newsletter-abo"],
        "groups": ["Mitglied / Portal", "Redakteur", "Leitung / Vorstand"],
        "calendar_categories": [
            {"name": "Kurse & Workshops", "color_state": 2, "is_shared": True, "is_public_default": True},
            {"name": "Veranstaltungen", "color_state": 1, "is_shared": True, "is_public_default": True},
        ],
    },
    "nas": {
        "label": "Privat / NAS-Hub",
        "icon": "bi-hdd-network",
        "description": "Dokumente, Kalender, Adressen, Listen & Suche für den privaten oder internen Einsatz.",
        "modules": ["master_data", "persons", "addresses", "documents", "global_search"],
        "enable_website": False,
        "blocks": [],
        "forms": [],
        "groups": ["Mitglied / Portal", "Mitarbeiter"],
        "calendar_categories": [
            {"name": "Familie / Privat", "color_state": 4, "is_shared": True, "is_public_default": False},
        ],
    },
    "custom": {
        "label": "Individuell",
        "icon": "bi-sliders",
        "description": "Alle Module, Bausteine, Formulare und Gruppen frei zusammenstellen.",
        "modules": ["master_data", "persons", "addresses", "documents", "global_search"],
        "enable_website": True,
        "blocks": ["hero", "text_image"],
        "forms": ["kontakt-anfragen"],
        "groups": ["Mitglied / Portal", "Redakteur", "Leitung / Vorstand"],
        "calendar_categories": [
            {"name": "Allgemein", "color_state": 1, "is_shared": True, "is_public_default": True},
        ],
    },
}

DOMAIN_MODULES = [
    ("master_data", "Stammdaten (Kategorien, Status, Rollen, Einheiten)"),
    ("persons", "Personen & Kontakte"),
    ("addresses", "Adressen & Standorte"),
    ("inventory", "Inventar, Räume & Ressourcen"),
    ("contracts", "Verträge & Vereinbarungen"),
    ("accounts", "Konten & Finanzen"),
    ("documents", "Dokumente & Downloads"),
    ("global_search", "Globale Suche"),
]

WEBSITE_BLOCKS = [
    ("hero", "Hero-Kopfbereich"),
    ("text_image", "Über uns (Text & Bild)"),
    ("news_feed", "News-Feed"),
    ("upcoming_events", "Nächste Termine"),
    ("people_grid", "Vorstand / Kontakte / Dozenten"),
    ("downloads", "Öffentliche Downloads"),
    ("faq_list", "FAQ-Akkordeon"),
]

FORM_PRESETS = [
    ("kontakt-anfragen", "Kontakt & Anfragen"),
    ("kurs-anmeldung", "Kurs- & Veranstaltungsanmeldung"),
    ("mitgliedsantrag", "Mitgliedsantrag"),
    ("kuendigung", "Kündigung / Abmeldung"),
    ("newsletter-abo", "Newsletter-Abo"),
]


def apply_wizard_setup(payload: dict, user=None) -> dict:
    """Idempotently apply setup wizard choices without overwriting existing customized content."""
    summary = {
        "modules_updated": False,
        "groups_created": 0,
        "pages_created": 0,
        "blocks_added": 0,
        "collections_created": 0,
        "calendar_categories_created": 0,
        "demo_seeded": [],
    }

    profile_key = (payload.get("profile_key") or "verein").strip()
    if profile_key not in WIZARD_PROFILES:
        profile_key = "custom"

    site_name = (payload.get("site_name") or "").strip()[:140]
    tagline = (payload.get("tagline") or "").strip()[:220]
    contact_email = (payload.get("contact_email") or "").strip()
    genre = (payload.get("genre") or "").strip()[:40]

    selected_modules = set(payload.get("modules") or [])
    enable_website = bool(payload.get("enable_website"))
    selected_blocks = list(payload.get("blocks") or [])
    selected_forms = list(payload.get("forms") or [])
    selected_groups = list(payload.get("groups") or [])
    custom_groups_raw = (payload.get("custom_groups") or "").strip()
    selected_cal_cats = list(payload.get("calendar_categories") or [])
    addons = set(payload.get("addons") or [])

    with transaction.atomic():
        # 1. domain_kit: modules + default groups/roles + custom groups
        if apps.is_installed("domain_kit"):
            from django.contrib.auth.models import Group
            from domain_kit.models import DomainModuleSettings, Role
            from domain_kit.services import ensure_group_permission_rows, seed_domain_defaults

            solo = DomainModuleSettings.get_solo()
            for mod_key, _ in DOMAIN_MODULES:
                field = f"enable_{mod_key}"
                if hasattr(solo, field):
                    setattr(solo, field, mod_key in selected_modules)
            if "inventory" in selected_modules or "contracts" in selected_modules or "accounts" in selected_modules:
                solo.enable_assets = True
            solo.save()
            summary["modules_updated"] = True

            seed_domain_defaults()
            if "academy" in addons or profile_key == "academy":
                Role.objects.get_or_create(name="Dozent / Referent", defaults={"color_state": 2, "position": 25})
            for gname in selected_groups:
                _, created = Group.objects.get_or_create(name=gname)
                if created:
                    summary["groups_created"] += 1
            for raw_g in custom_groups_raw.split(","):
                gname = raw_g.strip()[:150]
                if gname:
                    _, created = Group.objects.get_or_create(name=gname)
                    if created:
                        summary["groups_created"] += 1
            ensure_group_permission_rows()

        # 2. list_kit: collections for News, FAQ, and selected forms
        if apps.is_installed("list_kit") and user is not None:
            from list_kit.models import Collection
            from list_kit.services import seed_default_templates

            tpl_map = {t.slug: t for t in seed_default_templates()}
            if enable_website and "news_feed" in selected_blocks and "news-aktuelles" in tpl_map:
                if not Collection.objects.filter(slug="news").exists():
                    Collection.objects.create(
                        slug="news",
                        title="Aktuelles & News",
                        template=tpl_map["news-aktuelles"],
                        owner=user,
                        responsible_user=user,
                        is_public=True,
                    )
                    summary["collections_created"] += 1

            if enable_website and "faq_list" in selected_blocks and "faq" in tpl_map:
                if not Collection.objects.filter(slug="faq").exists():
                    Collection.objects.create(
                        slug="faq",
                        title="Häufige Fragen (FAQ)",
                        template=tpl_map["faq"],
                        owner=user,
                        responsible_user=user,
                        is_public=True,
                    )
                    summary["collections_created"] += 1

            form_titles = dict(FORM_PRESETS)
            for form_slug in selected_forms:
                tpl = tpl_map.get(form_slug)
                if not tpl:
                    continue
                if not Collection.objects.filter(slug=form_slug).exists():
                    Collection.objects.create(
                        slug=form_slug,
                        title=form_titles.get(form_slug, tpl.name),
                        template=tpl,
                        owner=user,
                        responsible_user=user,
                        is_public=True,
                        allow_public_submit=True,
                    )
                    summary["collections_created"] += 1

        # 3. site_kit: SiteConfig + Home Page + non-duplicate blocks
        if apps.is_installed("site_kit") and enable_website:
            from site_kit.models import PageBlock, PublicPage, SiteConfig

            cfg = SiteConfig.get_solo()
            if site_name:
                cfg.site_name = site_name
            if tagline:
                cfg.tagline = tagline
            if contact_email:
                cfg.contact_email = contact_email
            if genre:
                cfg.default_genre = genre
            cfg.save()

            home = PublicPage.objects.filter(is_home=True).first()
            if home is None:
                home = PublicPage.objects.create(
                    title=site_name or "Startseite",
                    is_home=True,
                    is_published=True,
                    show_in_nav=False,
                    genre=genre,
                )
                summary["pages_created"] += 1

            existing_types = set(home.blocks.values_list("block_type", flat=True))
            block_titles = dict(WEBSITE_BLOCKS)
            next_pos = (home.blocks.count() + 1) * 10
            for btype in selected_blocks:
                if btype in existing_types or btype not in dict(PageBlock.BLOCK_TYPE_CHOICES):
                    continue
                PageBlock.objects.create(
                    page=home,
                    block_type=btype,
                    title=site_name if btype == "hero" and site_name else block_titles.get(btype, ""),
                    subtitle=tagline if btype == "hero" else "",
                    body="Willkommen! Dieser Bereich wurde über den Ersteinrichtungs-Assistenten angelegt." if btype in ("hero", "text_image") else "",
                    position=next_pos,
                )
                next_pos += 10
                summary["blocks_added"] += 1

            if selected_forms and "public_form" not in existing_types:
                first_form = selected_forms[0]
                PageBlock.objects.create(
                    page=home,
                    block_type="public_form",
                    title=dict(FORM_PRESETS).get(first_form, "Kontakt & Anfrage"),
                    config_json={"collection_slug": first_form},
                    position=next_pos,
                )
                next_pos += 10
                summary["blocks_added"] += 1

            if ("academy" in addons or profile_key == "academy") and not home.blocks.filter(title="Unsere Dozenten").exists():
                PageBlock.objects.create(
                    page=home,
                    block_type="people_grid",
                    title="Unsere Dozenten",
                    config_json={"role_filter": "Dozent"},
                    position=next_pos,
                )
                summary["blocks_added"] += 1

        # 4. cal_kit: CalendarCategories
        if apps.is_installed("cal_kit") and user is not None:
            from cal_kit.models import CalendarCategory

            preset_cats = {c["name"]: c for c in WIZARD_PROFILES.get(profile_key, {}).get("calendar_categories", [])}
            for cname in selected_cal_cats:
                cname = cname.strip()[:80]
                if not cname:
                    continue
                cinfo = preset_cats.get(cname, {})
                _, created = CalendarCategory.objects.get_or_create(
                    user=user,
                    name=cname,
                    defaults={
                        "color_state": cinfo.get("color_state", 1),
                        "is_shared": cinfo.get("is_shared", True),
                        "is_public_default": cinfo.get("is_public_default", False),
                    },
                )
                if created:
                    summary["calendar_categories_created"] += 1

        # 5. Demo seeding via seed_kit registry
        if payload.get("run_demo_seed"):
            demo_count = max(1, min(50, int(payload.get("demo_count") or 5)))
            reset_demo = bool(payload.get("reset_demo"))
            summary["demo_seeded"] = run_seeders(count=demo_count, reset=reset_demo)

        state = SetupWizardState.get_solo()
        state.is_completed = True
        state.hide_on_start = bool(payload.get("hide_on_start", True))
        state.profile_key = profile_key
        state.config_snapshot_json = payload
        state.completed_at = timezone.now()
        state.save()

    return summary
