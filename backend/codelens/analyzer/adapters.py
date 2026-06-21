"""
Custom allauth social account adapter for CodeLens.
- Auto-generates a clean username from the user's email (no extra form needed)
- Ensures a UserProfile row exists after social signup
- Redirects to home after login
"""

import re
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User


class SocialAccountAdapter(DefaultSocialAccountAdapter):

    def get_login_redirect_url(self, request):
        """Always land on the home page after social login."""
        return '/'

    def pre_social_login(self, request, sociallogin):
        """
        Called after OAuth succeeds but before the user is created/logged in.
        If the email already matches an existing account, connect them instead
        of creating a duplicate.
        """
        if sociallogin.is_existing:
            return

        email = ''
        if sociallogin.account.extra_data:
            email = (
                sociallogin.account.extra_data.get('email') or
                sociallogin.account.extra_data.get('emails', [{}])[0].get('email', '')
                if isinstance(sociallogin.account.extra_data.get('emails'), list)
                else sociallogin.account.extra_data.get('email', '')
            )

        if email:
            try:
                existing_user = User.objects.get(email__iexact=email)
                sociallogin.connect(request, existing_user)
            except User.DoesNotExist:
                pass

    def save_user(self, request, sociallogin, form=None):
        """
        Override to auto-generate a username from email, ensuring no
        social signup form is ever shown.
        """
        user = super().save_user(request, sociallogin, form)

        # Ensure UserProfile exists
        from codelens.analyzer.models import UserProfile
        UserProfile.objects.get_or_create(user=user)

        return user

    def populate_user(self, request, sociallogin, data):
        """
        Fills in the User fields from social account data.
        Always auto-generates a clean, unique username matching name or email.
        """
        user = super().populate_user(request, sociallogin, data)

        # Extract name or other details from social logins
        extra_data = sociallogin.account.extra_data or {}
        first_name = (data.get('first_name') or '').strip()
        last_name = (data.get('last_name') or '').strip()
        name = (data.get('name') or '').strip()

        # If name is empty, fall back to sociallogin extra_data details
        if not name:
            name = (extra_data.get('name') or '').strip()

        # If first_name and last_name are not both set, try to derive them from name
        if name and not (first_name and last_name):
            parts = name.split(' ', 1)
            if not first_name:
                first_name = parts[0].strip()
            if not last_name and len(parts) > 1:
                last_name = parts[1].strip()

        # If first_name still contains spaces and last_name is empty (common in some logins)
        if first_name and not last_name:
            parts = first_name.split(' ', 1)
            if len(parts) > 1:
                first_name = parts[0].strip()
                last_name = parts[1].strip()

        # Try Google family_name and given_name from extra_data
        if not first_name and extra_data.get('given_name'):
            first_name = extra_data.get('given_name').strip()
        if not last_name and extra_data.get('family_name'):
            last_name = extra_data.get('family_name').strip()

        # Set them back on the user object
        user.first_name = first_name
        user.last_name = last_name

        # Build candidate base
        username_candidate = ""
        if first_name or last_name:
            username_candidate = f"{first_name}{last_name}"
        elif name:
            username_candidate = name
        elif extra_data.get('name'):
            username_candidate = extra_data.get('name')
        elif extra_data.get('login'):  # GitHub username
            username_candidate = extra_data.get('login')

        # Sanitize to lowercase alphanumeric and underscore
        username_candidate = re.sub(r'[^a-zA-Z0-9_]', '', username_candidate).lower()

        # Fallback to email prefix if name is not available
        if not username_candidate:
            email = data.get('email', '') or extra_data.get('email', '') or ''
            if email:
                username_candidate = re.sub(r'[^a-zA-Z0-9_]', '', email.split('@')[0]).lower()

        # Ultimate fallback
        if not username_candidate:
            username_candidate = 'user'

        # Ensure uniqueness across the entire User database
        candidate = username_candidate
        suffix = 1
        while User.objects.filter(username=candidate).exclude(pk=user.pk if user.pk else None).exists():
            candidate = f"{username_candidate}{suffix}"
            suffix += 1

        user.username = candidate
        return user
