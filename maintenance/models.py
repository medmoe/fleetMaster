from django.db import models
from vehicles.models import StatusChoices, Vehicle


class MaintenanceRecord(models.Model):
    """ Track each maintenance event for a vehicle """

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    service_date = models.DateField()
    service_type = models.CharField(max_length=100)
    description = models.TextField()
    mileage_at_service = models.PositiveIntegerField()
    next_service_due = models.DateField()
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.IN_MAINTENANCE)

    def __str__(self):
        return f'Service {self.id} for {self.vehicle} on {self.service_date}'


class Part(models.Model):
    """ Track individual parts that might be used in maintenance activities """

    name = models.CharField(max_length=100)
    part_number = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    quantity_in_stock = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.name} ({self.part_number})'


class MaintenancePart(models.Model):
    """ Link parts to maintenance records detailing which parts were used in a given maintenance event """

    maintenance_record = models.ForeignKey(MaintenanceRecord, on_delete=models.CASCADE)
    part = models.ForeignKey(Part, on_delete=models.CASCADE)
    quantity_used = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.part.name} used in Service {self.maintenance_record.id}'


class ServiceProvider(models.Model):
    """ Captures information about service providers or repair shops that perform the maintenance """

    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=254, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name


class ServiceRecord(models.Model):
    """ Connects maintenance records to service providers, capturing details about who performed the maintenance """

    maintenance_record = models.OneToOneField(MaintenanceRecord, on_delete=models.CASCADE)
    service_provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE)
    service_date = models.DateField()
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'Service Record for Maintenance {self.maintenance_record.id} by {self.service_provider}'


class ScheduledMaintenance(models.Model):
    """ schedule upcoming maintenance based on mileage or time intervals """

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    service_type = models.CharField(max_length=100)
    interval_mileage = models.PositiveIntegerField()
    interval_days = models.PositiveIntegerField()
    last_service_date = models.DateField()

    def __str__(self):
        return f'Scheduled Maintenance for {self.vehicle} every {self.interval_mileage} miles or {self.interval_days} days'
