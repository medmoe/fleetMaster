from django.db import models

# Create your models here.

from django.db import models


class VehicleTypeChoices(models.TextChoices):
    CAR = "CAR", "Car"
    TRUCK = "TRUCK", "Truck"
    MOTORCYCLE = "MOTORCYCLE", "Motorcycle"
    VAN = "VAN", "Van"


class StatusChoices(models.TextChoices):
    ACTIVE = "ACTIVE", 'Active'
    IN_MAINTENANCE = "IN_MAINTENANCE", "In maintenance"
    OUT_OF_SERVICE = "OUT_OF_SERVICE", "Out of service"


class Vehicle(models.Model):
    registration_number = models.CharField(max_length=20, unique=True)
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.PositiveIntegerField()
    vin = models.CharField(max_length=17, unique=True)
    color = models.CharField(max_length=30)
    type = models.CharField(max_length=20, choices=VehicleTypeChoices.choices)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE)
    purchase_date = models.DateField()
    last_service_date = models.DateField()
    next_service_due = models.DateField()
    mileage = models.PositiveIntegerField()
    fuel_type = models.CharField(max_length=20)
    capacity = models.PositiveIntegerField()
    insurance_policy_number = models.CharField(max_length=50)
    insurance_expiry_date = models.DateField()
    license_expiry_date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.make} {self.model} ({self.registration_number})'
