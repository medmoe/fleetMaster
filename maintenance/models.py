from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.db.models import Sum


class ServiceChoices(models.TextChoices):
    MECHANIC = "MECHANIC", "Mechanic"
    ELECTRICIAN = "ELECTRICIAN", "Electrician"
    CLEANING = "CLEANING", "Cleaning"


class MaintenanceChoices(models.TextChoices):
    PREVENTIVE = 'PREVENTIVE', "Preventive"
    CURATIVE = 'CURATIVE', "Curative"


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


class MaintenanceReport(models.Model):
    profile = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE)
    maintenance_type = models.CharField(max_length=50, choices=MaintenanceChoices.choices, default=MaintenanceChoices.PREVENTIVE)
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField(blank=True)
    mileage = models.PositiveIntegerField(blank=True, null=True)

    @property
    def total_cost(self):
        parts_cost = self.part_purchase_events.aggregate(total=Sum('cost'))['total'] or 0
        services_cost = self.service_provider_events.aggregate(total=Sum('cost'))['total'] or 0
        return parts_cost + services_cost

    def clean(self):
        if self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date.")



class PartPurchaseEvent(models.Model):
    part = models.ForeignKey(Part, on_delete=models.CASCADE)
    provider = models.ForeignKey(PartsProvider, on_delete=models.CASCADE)
    maintenance_report = models.ForeignKey(MaintenanceReport, on_delete=models.CASCADE, related_name='part_purchase_events')
    purchase_date = models.DateField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    receipt = models.ImageField(upload_to='parts/%Y/%m/%d/', null=True)

class ServiceProviderEvent(models.Model):
    maintenance_report = models.ForeignKey(MaintenanceReport, on_delete=models.CASCADE, related_name='service_provider_events')
    service_provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE)
    service_date = models.DateField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    receipt = models.ImageField(upload_to='services/%Y/%m/%d/', null=True)
    description = models.TextField(blank=True)

class VehicleEvent(models.Model):
    maintenance_report = models.ForeignKey(MaintenanceReport, on_delete=models.CASCADE, related_name='vehicle_events')
    vehicle = models.ForeignKey("vehicles.Vehicle", on_delete=models.CASCADE)



