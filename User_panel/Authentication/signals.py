from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from allauth.socialaccount.signals import social_account_updated


def update_google_name(user, sociallogin):
    if sociallogin.account.provider != "google":
        return

    google_data = sociallogin.account.extra_data
    full_name = google_data.get("name", "").strip()

    if not full_name:
        first_name = google_data.get("given_name", "").strip()
        last_name = google_data.get("family_name", "").strip()
        full_name = f"{first_name} {last_name}".strip()

    if full_name and user.full_name != full_name:
        user.full_name = full_name
        user.save(update_fields=["full_name"])


@receiver(user_signed_up)
def google_user_signed_up(request, user, sociallogin=None, **kwargs):
    if sociallogin:
        update_google_name(user, sociallogin)


@receiver(social_account_updated)
def google_account_updated(request, sociallogin, **kwargs):
    update_google_name(sociallogin.user, sociallogin)