from django.db import models
from vehicles.models import Vehicle
from accounts.models import UserProfile


class EmploymentStatusChoices(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"
    ON_LEAVE = "ON_LEAVE", "On leave"


class Driver(models.Model):
    profile = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE)
    vehicles = models.ManyToManyField(Vehicle)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.CharField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=100)
    licence_number = models.CharField(max_length=100, unique=True)
    licence_expiry_date = models.DateField()
    date_of_birth = models.DateField()
    address = models.CharField(max_length=150)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    profile_picture = models.ImageField(upload_to='media/profile_pics', null=True)
    hire_date = models.DateField()
    employment_status = models.CharField(max_length=100,
                                         choices=EmploymentStatusChoices.choices,
                                         default=EmploymentStatusChoices.ACTIVE)
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=100)
    notes = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'
