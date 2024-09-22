from rest_framework import serializers

from .models import Part, ServiceProvider, PartsProvider, PartPurchaseEvent, MaintenanceReport


class PartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Part
        fields = "__all__"


class ServiceProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProvider
        fields = "__all__"


class PartsProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartsProvider
        fields = "__all__"


class PartsPurchaseEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartPurchaseEvent
        fields = "__all__"


class MaintenanceReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceReport
        fields = "__all__"
