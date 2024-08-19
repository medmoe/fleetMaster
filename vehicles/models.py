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
    profile = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE)
    registration_number = models.CharField(max_length=100, unique=True, blank=True)
    make = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    year = models.PositiveIntegerField(blank=True)
    vin = models.CharField(max_length=100, unique=True, blank=True)
    color = models.CharField(max_length=100, blank=True)
    type = models.CharField(max_length=100, choices=VehicleTypeChoices.choices, default=VehicleTypeChoices.TRUCK)
    status = models.CharField(max_length=100, choices=StatusChoices.choices, default=StatusChoices.ACTIVE)
    purchase_date = models.DateField(blank=True)
    last_service_date = models.DateField(blank=True)
    next_service_due = models.DateField(blank=True)
    mileage = models.PositiveIntegerField(blank=True)
    fuel_type = models.CharField(max_length=100, blank=True)
    capacity = models.PositiveIntegerField(blank=True)
    insurance_policy_number = models.CharField(max_length=100, blank=True)
    insurance_expiry_date = models.DateField(blank=True)
    license_expiry_date = models.DateField(blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.make} {self.model} ({self.registration_number})'
