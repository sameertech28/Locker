"""Custom allauth adapter for Locker application."""
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings


class LockerAccountAdapter(DefaultAccountAdapter):
    """Custom account adapter that auto-creates vault profiles on signup."""

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        if commit:
            user.save()
        return user

    def get_login_redirect_url(self, request):
        return settings.LOGIN_REDIRECT_URL


class LockerSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom social account adapter for Google OAuth flow."""

    def pre_social_login(self, request, sociallogin):
        """Link social account to existing user with same email."""
        if sociallogin.is_existing:
            return
        email = sociallogin.account.extra_data.get("email")
        if email:
            from django.contrib.auth.models import User
            try:
                existing_user = User.objects.get(email=email)
                sociallogin.connect(request, existing_user)
            except User.DoesNotExist:
                pass

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        if not user.first_name:
            user.first_name = data.get("first_name", "")
        if not user.last_name:
            user.last_name = data.get("last_name", "")
        return user
