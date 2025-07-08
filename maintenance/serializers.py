from django.db import transaction
from rest_framework import serializers

from vehicles.serializers import VehicleSerializer
from .models import Part, ServiceProvider, PartsProvider, PartPurchaseEvent, MaintenanceReport, ServiceProviderEvent


class OwnedResourceSerializer(serializers.ModelSerializer):
    """Base serializer for resources owned by a user profile."""
    is_owner = serializers.SerializerMethodField(read_only=True)

    def get_is_owner(self, obj):
        """Check if the current user is the owner of the object."""
        return obj.profile == self.context['request'].user.userprofile

    def create(self, validated_data):
        """Create a new instance owned by the current user."""
        profile = self.context['request'].user.userprofile
        return self.Meta.model.objects.create(profile=profile, **validated_data)


class PartSerializer(OwnedResourceSerializer):
    class Meta:
        model = Part
        fields = "__all__"


class ServiceProviderSerializer(OwnedResourceSerializer):
    class Meta:
        model = ServiceProvider
        fields = "__all__"


class PartsProviderSerializer(OwnedResourceSerializer):
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
        read_only_fields = ['profile', 'total_cost']

    def _calculate_total_cost(self, part_events, service_events):
        """Calculate the total cost from part purchases and service events."""
        part_costs = sum(event.get('cost', 0) for event in part_events)
        service_costs = sum(event.get('cost', 0) for event in service_events)
        return part_costs + service_costs

    def _validate_service_events(self, service_events):
        """Validate that at least one service provider event exists."""
        if not service_events:
            raise serializers.ValidationError("At least one service provider event is required")

    def create(self, validated_data):
        profile = self.context['request'].user.userprofile
        part_purchase_events_data = validated_data.pop('part_purchase_events', [])
        service_provider_events_data = validated_data.pop('service_provider_events', [])

        self._validate_service_events(service_provider_events_data)
        total_cost = self._calculate_total_cost(part_purchase_events_data, service_provider_events_data)

        with transaction.atomic():
            maintenance_report = MaintenanceReport.objects.create(
                profile=profile, total_cost=total_cost, **validated_data
            )
            # Create related objects
            PartPurchaseEvent.objects.bulk_create(
                [PartPurchaseEvent(maintenance_report=maintenance_report, **part_data)
                 for part_data in part_purchase_events_data]
            )
            ServiceProviderEvent.objects.bulk_create(
                [ServiceProviderEvent(maintenance_report=maintenance_report, **service_event)
                 for service_event in service_provider_events_data]
            )

        return maintenance_report

    def update(self, instance, validated_data):
        part_purchase_events_data = validated_data.pop('part_purchase_events', [])
        service_provider_events_data = validated_data.pop('service_provider_events', [])
        validated_data.pop('vehicle_details', None)

        self._validate_service_events(service_provider_events_data)
        total_cost = self._calculate_total_cost(part_purchase_events_data, service_provider_events_data)

        with transaction.atomic():
            # Update main instance fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.total_cost = total_cost
            instance.save()

            # Update related objects
            self._update_maintenance_report_events(
                ["part_details", "provider_details"],
                PartPurchaseEvent,
                part_purchase_events_data,
                instance
            )
            self._update_maintenance_report_events(
                ["service_provider_details"],
                ServiceProviderEvent,
                service_provider_events_data,
                instance
            )

        return instance

    def _update_maintenance_report_events(self, keys_to_remove, model, events_data, maintenance_report_instance):
        """Update the events related to a maintenance report.

        Args:
            keys_to_remove: List of keys to remove from event data before creating new events
            model: The model class for the events
            events_data: List of event data dictionaries
            maintenance_report_instance: The maintenance report instance
        """
        event_ids_to_keep = []
        events_to_create = []

        # Prepare data
        for event in events_data:
            if "id" in event:
                event_ids_to_keep.append(event["id"])
            else:
                # Clean event data
                cleaned_event = event.copy()
                for key in keys_to_remove + ['maintenance_report']:
                    cleaned_event.pop(key, None)
                events_to_create.append(cleaned_event)

        # Remove events not in the keep list
        model.objects.filter(maintenance_report=maintenance_report_instance).exclude(pk__in=event_ids_to_keep).delete()

        # Create new events
        model.objects.bulk_create([
            model(maintenance_report=maintenance_report_instance, **event_data)
            for event_data in events_to_create
        ])
