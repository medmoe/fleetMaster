from django.db import transaction
from rest_framework import serializers

from vehicles.serializers import VehicleSerializer
from .models import Part, ServiceProvider, PartsProvider, PartPurchaseEvent, MaintenanceReport, ServiceProviderEvent


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


class PartPurchaseEventSerializer(serializers.ModelSerializer):
    part = serializers.PrimaryKeyRelatedField(queryset=Part.objects.all())
    provider_details = PartsProviderSerializer(source='provider', read_only=True)
    part_details = PartSerializer(source='part', read_only=True)
    maintenance_report = serializers.PrimaryKeyRelatedField(queryset=MaintenanceReport.objects.all(), required=False)

    class Meta:
        model = PartPurchaseEvent
        fields = "__all__"


class ServiceProviderEventSerializer(serializers.ModelSerializer):
    maintenance_report = serializers.PrimaryKeyRelatedField(queryset=MaintenanceReport.objects.all(), required=False)
    service_provider_details = ServiceProviderSerializer(source='service_provider', read_only=True)

    class Meta:
        model = ServiceProviderEvent
        fields = "__all__"


class MaintenanceReportSerializer(serializers.ModelSerializer):
    part_purchase_events = PartPurchaseEventSerializer(many=True, required=False)
    service_provider_events = ServiceProviderEventSerializer(many=True, required=False)
    vehicle_details = VehicleSerializer(source='vehicle', read_only=True)

    class Meta:
        model = MaintenanceReport
        fields = "__all__"
        read_only_fields = ['profile']

    def create(self, validated_data):
        try:
            return self._handle_maintenance_report_events(validated_data, is_new=True)
        except Exception as e:
            raise serializers.ValidationError(f"Error creating maintenance report: {e}")

    def update(self, instance, validated_data):
        try:
            return self._handle_maintenance_report_events(validated_data, is_new=False, instance=instance)
        except Exception as e:
            raise serializers.ValidationError(f"Error updating maintenance report: {e}")

    def _handle_maintenance_report_events(self, validated_data, is_new=True, instance=None):
        """
        Handles the creation or update of MaintenanceReport and associated events.

        Args:
            validated_data: Validated data for creating or updating a MaintenanceReport.
            is_new: Boolean indicating whether the operation is for a new MaintenanceReport.
            instance: Existing MaintenanceReport instance, if updating.
        """
        profile = self.context['request'].user.userprofile
        part_purchase_events_data = validated_data.pop('part_purchase_events', [])
        service_provider_events_data = validated_data.pop('service_provider_events', [])
        with transaction.atomic():
            if is_new:
                maintenance_report = MaintenanceReport.objects.create(profile=profile, **validated_data)
            else:
                maintenance_report = instance
                for attr, value in validated_data.items():
                    setattr(maintenance_report, attr, value)
                maintenance_report.save()
            PartPurchaseEvent.objects.bulk_create(
                [PartPurchaseEvent(maintenance_report=maintenance_report, **part_data) for part_data in part_purchase_events_data]
            )
            ServiceProviderEvent.objects.bulk_create(
                [ServiceProviderEvent(maintenance_report=maintenance_report, **service_event) for service_event in service_provider_events_data]
            )
        return maintenance_report
