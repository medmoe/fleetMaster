import datetime
import random

from django.db import models

from accounts.models import UserProfile


class EmploymentStatusChoices(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"
    ON_LEAVE = "ON_LEAVE", "On leave"


class AbsenceChoices(models.TextChoices):
    MAINTENANCE = "MAINTENANCE", "Maintenance"
    SICKNESS = "SICKNESS", "Sickness"
    OTHER = "OTHER", "Other"


class Driver(models.Model):
    profile = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE)
    vehicle = models.ForeignKey("vehicles.Vehicle", on_delete=models.CASCADE, null=True, blank=True, )
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=100, unique=True)
    license_number = models.CharField(max_length=100, unique=True)
    license_expiry_date = models.DateField(blank=True)
    date_of_birth = models.DateField(blank=True)
    address = models.CharField(max_length=150, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True)
    hire_date = models.DateField(blank=True)
    employment_status = models.CharField(max_length=100, choices=EmploymentStatusChoices.choices, default=EmploymentStatusChoices.ACTIVE)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    access_code = models.CharField(max_length=8, unique=True, blank=True, null=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    def generate_access_code(self):
        """Generate a unique 6-character access code for the driver."""

        def calculate_checksum(code):
            return str(sum(ord(c) for c in code) % 10)

        chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
        while True:
            code = "".join(random.choices(chars, k=6))
            checksum = calculate_checksum(code)
            full_code = f'{code}-{checksum}'
            if not Driver.objects.filter(access_code=full_code).exists():
                return full_code

    def save(self, *args, **kwargs):
        if not self.access_code:
            self.access_code = self.generate_access_code()
        super().save(*args, **kwargs)


class DriverStartingShift(models.Model):
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='shifts')
    date = models.DateField(default=datetime.date.today)
    time = models.TimeField()
    load = models.PositiveIntegerField()
    mileage = models.PositiveIntegerField()
    delivery_areas = models.JSONField(default=list)
    status = models.BooleanField(default=True)
    absence_type = models.CharField(max_length=100, choices=AbsenceChoices.choices, blank=True, null=True)
    absence_description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'{self.driver.first_name} {self.driver.last_name} - {self.date} - {self.time}'
