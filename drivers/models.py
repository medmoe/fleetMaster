from django.db import models
from accounts.models import UserProfile


class EmploymentStatusChoices(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"
    ON_LEAVE = "ON_LEAVE", "On leave"


class Driver(models.Model):
    profile = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE)
    vehicle = models.ForeignKey("vehicles.Vehicle", on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.CharField(max_length=255, blank=True, unique=True, null=True)
    phone_number = models.CharField(max_length=100, unique=True)
    license_number = models.CharField(max_length=100, unique=True, blank=True)
    license_expiry_date = models.DateField(blank=True)
    date_of_birth = models.DateField(blank=True)
    address = models.CharField(max_length=150, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True)
    hire_date = models.DateField(blank=True)
    employment_status = models.CharField(max_length=100,
                                         choices=EmploymentStatusChoices.choices,
                                         default=EmploymentStatusChoices.ACTIVE)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'
