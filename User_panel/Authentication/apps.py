from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"

    name = "User_panel.Authentication"


    def ready(self):
        import User_panel.Authentication.signals