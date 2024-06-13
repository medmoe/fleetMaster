from django.db import models
from django.contrib.auth.models import User


# Create your models here.

class UserProfile(models.Model):
    """ Defines the user profile in the system """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=50, blank=True)
    state = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=50, blank=True)
    zip_code = models.CharField(max_length=50, blank=True)
    sign_up_date = models.DateTimeField(auto_now_add=True)
    last_login_date = models.DateTimeField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username
