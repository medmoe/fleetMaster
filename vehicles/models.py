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
    """
    Vehicle Class for managing vehicle details.

    Attributes:
        profile (ForeignKey): Foreign key to the user profile associated with the vehicle.
        registration_number (CharField): Unique registration number of the vehicle.
        make (CharField): Make of the vehicle.
        model (CharField): Model of the vehicle.
        year (PositiveIntegerField): Year of the vehicle.
        vin (CharField): Unique vehicle identification number.
        color (CharField): Color of the vehicle.
        type (CharField): Type of the vehicle (choices: TRUCK, CAR, MOTORCYCLE).
        status (CharField): Status of the vehicle (choices: ACTIVE, INACTIVE).
        purchase_date (DateField): Date of purchase of the vehicle.
        last_service_date (DateField): Date of the last service of the vehicle.
        next_service_due (DateField): Date of the next service due for the vehicle.
        mileage (PositiveIntegerField): Mileage of the vehicle.
        fuel_type (CharField): Fuel type of the vehicle.
        capacity (PositiveIntegerField): Capacity of the vehicle.
        insurance_policy_number (CharField): Insurance policy number of the vehicle.
        insurance_expiry_date (DateField): Date of expiry of the insurance policy.
        license_expiry_date (DateField): Date of expiry of the vehicle's license.
        notes (TextField): Additional notes or comments about the vehicle.
        created_at (DateTimeField): Date and time when the vehicle object was created.
        updated_at (DateTimeField): Date and time when the vehicle object was last updated.

    Methods:
        __str__(self): Returns a string representation of the vehicle.

    """
    profile = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE)
    registration_number = models.CharField(max_length=100, blank=True)
    make = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    year = models.PositiveIntegerField(blank=True)
    vin = models.CharField(max_length=100, blank=True)
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
