from django.urls import path

from . import views

app_name = "seed_kit"

urlpatterns = [
    path("", views.setup_wizard_view, name="wizard"),
    path("apply/", views.setup_wizard_apply_view, name="wizard_apply"),
    path("dismiss/", views.setup_wizard_dismiss_view, name="wizard_dismiss"),
]
