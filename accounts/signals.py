from allauth.socialaccount.signals import social_account_added
from django.dispatch import receiver

from .models import UserProfile


# This specifically handles social account creation
@receiver(social_account_added)
def create_social_account(request, sociallogin, **kwargs):
    if not UserProfile.objects.filter(user=sociallogin.user).exists():
        UserProfile.objects.get_or_create(user=sociallogin.user)
