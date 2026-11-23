import json

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import SetupWizardState
from .services import (
    DOMAIN_MODULES,
    FORM_PRESETS,
    WEBSITE_BLOCKS,
    WIZARD_PROFILES,
    apply_wizard_setup,
)


@login_required
def setup_wizard_view(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("Admin-Zugriff erforderlich.")
    state = SetupWizardState.get_solo()
    genres = []
    try:
        from design_studio.genres import GENRE_CHOICES
        genres = list(GENRE_CHOICES)
    except Exception:
        genres = []

    installed_kits = {
        "domain_kit": apps.is_installed("domain_kit"),
        "site_kit": apps.is_installed("site_kit"),
        "list_kit": apps.is_installed("list_kit"),
        "cal_kit": apps.is_installed("cal_kit"),
        "notify_kit": apps.is_installed("notify_kit"),
    }

    current_site_name = ""
    current_tagline = ""
    current_email = ""
    if installed_kits["site_kit"]:
        try:
            from site_kit.models import SiteConfig
            cfg = SiteConfig.get_solo()
            current_site_name = cfg.site_name
            current_tagline = cfg.tagline
            current_email = cfg.contact_email
        except Exception:
            pass

    return render(
        request,
        "seed_kit/setup_wizard.html",
        {
            "wizard_state": state,
            "profiles": WIZARD_PROFILES,
            "profiles_json": json.dumps(WIZARD_PROFILES),
            "domain_modules": DOMAIN_MODULES,
            "website_blocks": WEBSITE_BLOCKS,
            "form_presets": FORM_PRESETS,
            "genres": genres,
            "installed_kits": installed_kits,
            "current_site_name": current_site_name,
            "current_tagline": current_tagline,
            "current_email": current_email,
        },
    )


@login_required
@require_POST
def setup_wizard_apply_view(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("Admin-Zugriff erforderlich.")
    payload = {
        "profile_key": request.POST.get("profile_key") or "verein",
        "site_name": request.POST.get("site_name") or "",
        "tagline": request.POST.get("tagline") or "",
        "contact_email": request.POST.get("contact_email") or "",
        "genre": request.POST.get("genre") or "",
        "modules": request.POST.getlist("modules"),
        "enable_website": request.POST.get("enable_website") == "on",
        "blocks": request.POST.getlist("blocks"),
        "forms": request.POST.getlist("forms"),
        "groups": request.POST.getlist("groups"),
        "custom_groups": request.POST.get("custom_groups") or "",
        "calendar_categories": [
            c.strip() for c in (request.POST.get("calendar_categories_text") or "").split(",") if c.strip()
        ],
        "run_demo_seed": request.POST.get("run_demo_seed") == "on",
        "demo_count": request.POST.get("demo_count") or 5,
        "reset_demo": request.POST.get("reset_demo") == "on",
        "hide_on_start": request.POST.get("hide_on_start") == "on",
    }
    summary = apply_wizard_setup(payload, user=request.user)
    messages.success(
        request,
        f"Einrichtung abgeschlossen (Gruppen: +{summary['groups_created']}, Blöcke: +{summary['blocks_added']}, Formulare/Listen: +{summary['collections_created']}, Kalender: +{summary['calendar_categories_created']}).",
    )
    return redirect("seed_kit:wizard")


@login_required
@require_POST
def setup_wizard_dismiss_view(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("Admin-Zugriff erforderlich.")
    state = SetupWizardState.get_solo()
    state.hide_on_start = True
    state.save(update_fields=["hide_on_start", "updated_at"])
    messages.info(request, "Ersteinrichtungs-Assistent für den Start ausgeblendet. Sie können ihn jederzeit unter /setup/ erneut öffnen.")
    return redirect("/")
