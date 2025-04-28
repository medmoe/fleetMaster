from django.db import transaction
from rest_framework import serializers

from vehicles.serializers import VehicleSerializer
from .models import Part, ServiceProvider, PartsProvider, PartPurchaseEvent, MaintenanceReport, ServiceProviderEvent


class PartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Part
        fields = "__all__"


    def create(self, validated_data):
        profile = self.context['request'].user.userprofile
        return Part.objects.create(profile=profile, **validated_data)

class ServiceProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProvider
        fields = "__all__"

    def create(self, validated_data):
        profile = self.context['request'].user.userprofile
        return ServiceProvider.objects.create(profile=profile, **validated_data)


class PartsProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartsProvider
        fields = "__all__"

    def create(self, validated_data):
        profile = self.context['request'].user.userprofile
        return PartsProvider.objects.create(profile=profile, **validated_data)


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
    total_cost = serializers.SerializerMethodField()

    class Meta:
        model = MaintenanceReport
        fields = [
            "id",
            "profile",
            "vehicle",
            "vehicle_details",
            "maintenance_type",
            "start_date",
            "end_date",
            "description",
            "mileage",
            "total_cost",
            "part_purchase_events",
            "service_provider_events",
        ]
        read_only_fields = ['profile']

    def get_total_cost(self, obj):
        return obj.total_cost

    def create(self, validated_data):
        profile = self.context['request'].user.userprofile
        part_purchase_events_data = validated_data.pop('part_purchase_events', [])
        service_provider_events_data = validated_data.pop('service_provider_events', [])
        if not service_provider_events_data:
            raise serializers.ValidationError("At least one service provider event is required")

        with transaction.atomic():
            maintenance_report = MaintenanceReport.objects.create(profile=profile, **validated_data)
            PartPurchaseEvent.objects.bulk_create(
                [PartPurchaseEvent(maintenance_report=maintenance_report, **part_data) for part_data in part_purchase_events_data]
            )
            ServiceProviderEvent.objects.bulk_create(
                [ServiceProviderEvent(maintenance_report=maintenance_report, **service_event) for service_event in service_provider_events_data]
            )
        return maintenance_report

    def update(self, instance, validated_data):
        part_purchase_events_data = validated_data.pop('part_purchase_events', [])
        service_provider_events_data = validated_data.pop('service_provider_events', [])
        if not service_provider_events_data and not ServiceProviderEvent.objects.filter(maintenance_report=instance).exists():
            raise serializers.ValidationError("At least one service provider event is required")

        validated_data.pop('vehicle_details', None)
        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            # Handle part purchase events
            if part_purchase_events_data:
                provided_part_purchase_event_ids = {event.get('id') for event in part_purchase_events_data}
                if provided_part_purchase_event_ids:
                    PartPurchaseEvent.objects.filter(maintenance_report=instance).exclude(pk__in=provided_part_purchase_event_ids).delete()

            # Process each event in the request
            for part_purchase_event in part_purchase_events_data:
                part_purchase_event.pop('part_details', None)
                part_purchase_event.pop('provider_details', None)
                part_purchase_event.pop('maintenance_report', None)
                if not 'id' in part_purchase_event:
                    PartPurchaseEvent.objects.create(maintenance_report=instance, **part_purchase_event)

            # Handle service events
            service_event_ids = {event.get('id') for event in service_provider_events_data}
            if service_event_ids:
                ServiceProviderEvent.objects.filter(maintenance_report=instance).exclude(pk__in=service_event_ids).delete()

            for service_event in service_provider_events_data:
                service_event.pop('service_provider_details', None)
                service_event.pop('maintenance_report', None)
                if not 'id' in service_event:
                    ServiceProviderEvent.objects.create(maintenance_report=instance, **service_event)

        return instance
