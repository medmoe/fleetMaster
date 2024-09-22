from django.db import models

from vehicles.models import Vehicle


class ServiceChoices(models.TextChoices):
    MECHANIC = "MECHANIC", "Mechanic"
    ELECTRICIAN = "ELECTRICIAN", "Electrician"
    CLEANING = "CLEANING", "Cleaning"


class Part(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class ServiceProvider(models.Model):
    name = models.CharField(max_length=100)
    service_type = models.CharField(max_length=100, choices=ServiceChoices.choices, default=ServiceChoices.MECHANIC)
    phone_number = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name


class PartsProvider(models.Model):
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=100)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name


class PartPurchaseEvent(models.Model):
    part = models.ForeignKey(Part, on_delete=models.CASCADE)
    provider = models.ForeignKey(PartsProvider, on_delete=models.CASCADE)
    purchase_date = models.DateField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    receipt = models.ImageField(upload_to='parts/{%Y}/{%m}/{%d}/', null=True)


class MaintenanceReport(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='maintenance_reports')
    service_provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name='maintenance_reports')
    start_date = models.DateField()
    end_date = models.DateField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    parts = models.ManyToManyField(PartPurchaseEvent, related_name='maintenance_reports')
    description = models.TextField(blank=True)
    mileage = models.PositiveIntegerField(blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.vehicle.mileage = self.mileage
        self.vehicle.save()
