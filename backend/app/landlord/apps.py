from django.apps import AppConfig


class LandlordConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "landlord"
    verbose_name = "Landlord Domain"

    def ready(self):
        import landlord.signals  # noqa: F401
