from django.db import models


class SetupWizardState(models.Model):
    is_completed = models.BooleanField(default=False)
    hide_on_start = models.BooleanField(default=False)
    profile_key = models.CharField(max_length=40, blank=True, default="verein")
    config_snapshot_json = models.JSONField(default=dict, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"SetupWizardState(completed={self.is_completed}, profile={self.profile_key})"
