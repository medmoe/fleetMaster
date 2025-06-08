from django.contrib import admin

from .models import MaintenanceReport, Part, ServiceProvider, PartsProvider, PartPurchaseEvent, ServiceProviderEvent

# Register your models here.

admin.site.register(MaintenanceReport)
admin.site.register(Part)
admin.site.register(ServiceProvider)
admin.site.register(PartsProvider)
admin.site.register(PartPurchaseEvent)
admin.site.register(ServiceProviderEvent)
