from django.db import models
from vehicles.models import Vehicle


class EmploymentStatusChoices(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"
    ON_LEAVE = "ON_LEAVE", "On leave"


class Driver(models.Model):
    vehicles = models.ManyToManyField(Vehicle)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.CharField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=50)
    licence_number = models.CharField(max_length=100, unique=True)
    licence_expiry_date = models.DateField()
    date_of_birth = models.DateField()
    address = models.CharField(max_length=150)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=50)
    profile_picture = models.ImageField(upload_to='profile_pics/')
    hire_date = models.DateField()
    employment_status = models.CharField(max_length=20,
                                         choices=EmploymentStatusChoices.choices,
                                         default=EmploymentStatusChoices.ACTIVE)
    emergency_contact_name = models.CharField(max_length=50)
    emergency_contact_phone = models.CharField(max_length=50)
    notes = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'
