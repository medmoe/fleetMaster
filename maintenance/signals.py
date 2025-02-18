from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import MaintenanceReport
from vehicles.models import Vehicle

# Sync mileage from the latest MaintenanceReport to Vehicle
@receiver(post_save, sender=MaintenanceReport)
def sync_latest_mileage_to_vehicle(sender, instance, created, **kwargs):
    vehicle = instance.vehicle
    # Get the latest report by start_date for this vehicle
    latest_report = vehicle.maintenance_reports.order_by('-start_date').first()
    if latest_report == instance:
        if vehicle.mileage != instance.mileage:
            vehicle.mileage = instance.mileage
            vehicle.save()

# Handle the case where a Maintenance is deleted
@receiver(post_delete, sender=MaintenanceReport)
def handle_maintenance_report_deleted(sender, instance, **kwargs):
    vehicle = instance.vehicle
    latest_report = vehicle.maintenance_reports.order_by('-start_date').first()
    if latest_report:
        vehicle.mileage = latest_report.mileage
    else:
        vehicle.mileage = 0

    vehicle.save()