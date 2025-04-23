from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.signals import social_account_added

from .models import UserProfile

# This specifically handles social account creation
@receiver(social_account_added)
def create_social_account(request, sociallogin, **kwargs):
    if not UserProfile.objects.filter(user=sociallogin.user).exists():
        UserProfile.objects.create(user=sociallogin.user)