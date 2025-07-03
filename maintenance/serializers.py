from collections import defaultdict

from django.db import transaction
from rest_framework import serializers

from vehicles.serializers import VehicleSerializer
from .models import Part, ServiceProvider, PartsProvider, PartPurchaseEvent, MaintenanceReport, ServiceProviderEvent


class PartSerializer(serializers.ModelSerializer):
    isOwner = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = Part
        fields = "__all__"

    def get_isOwner(self, obj):
        return obj.profile == self.context['request'].user.userprofile

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

    def create(self, validated_data):
        profile = self.context['request'].user.userprofile
        part_purchase_events_data = validated_data.pop('part_purchase_events', [])
        service_provider_events_data = validated_data.pop('service_provider_events', [])
        if not service_provider_events_data:
            raise serializers.ValidationError("At least one service provider event is required")

        total_cost = sum(event.get('cost', 0) for event in part_purchase_events_data)
        total_cost += sum(event.get('cost', 0) for event in service_provider_events_data)

        with transaction.atomic():
            maintenance_report = MaintenanceReport.objects.create(profile=profile, total_cost=total_cost, **validated_data)

            # Create related objects
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
        validated_data.pop('vehicle_details', None)
        if not service_provider_events_data:
            raise serializers.ValidationError("At least one service provider event is required")

        # Calculate total cost and count parts upfront
        total_cost = sum(event.get('cost', 0) for event in part_purchase_events_data)
        total_cost += sum(event.get('cost', 0) for event in service_provider_events_data)

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            setattr(instance, 'total_cost', total_cost)
            instance.save()

            # Update related objects
            self._update_maintenance_report_events(["part_details", "provider_details"], PartPurchaseEvent, part_purchase_events_data, instance)
            self._update_maintenance_report_events(["service_provider_details"], ServiceProviderEvent, service_provider_events_data, instance)

        return instance

    def _update_maintenance_report_events(self, keys, model, events_data, maintenance_report_instance):
        events_to_keep, events_to_create = set(), list()
        keys.append('maintenance_report')
        for event in events_data:
            if "id" in event:
                events_to_keep.add(event)
            else:
                for key in keys:
                    event.pop(key, None)
                events_to_create.append(event)

        # Remove dangling events
        model.objects.filter(maintenance_report=maintenance_report_instance).exclude(pk__in=events_to_keep).delete()
        # Create new events
        model.objects.bulk_create([model(maintenance_report=maintenance_report_instance, **event_data) for event_data in events_to_create])
