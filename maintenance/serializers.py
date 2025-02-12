from django.db import transaction
from rest_framework import serializers

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
        read_only_fields = ['profile']


class ServiceProviderEventSerializer(serializers.ModelSerializer):
    maintenance_report = serializers.PrimaryKeyRelatedField(queryset=MaintenanceReport.objects.all(), required=False)

    class Meta:
        model = ServiceProviderEvent
        fields = "__all__"
        read_only_fields = ['profile']


class MaintenanceReportSerializer(serializers.ModelSerializer):
    part_purchase_events = PartPurchaseEventSerializer(many=True, required=False)
    service_provider_events = ServiceProviderEventSerializer(many=True, required=False)

    class Meta:
        model = MaintenanceReport
        fields = "__all__"
        read_only_fields = ['profile']

    def create(self, validated_data):
        profile = self.context['request'].user.userprofile
        part_purchase_events_data = validated_data.pop('part_purchase_events', [])
        service_provider_events_data = validated_data.pop('service_provider_events', [])
        try:
            with transaction.atomic():
                maintenance_report = MaintenanceReport.objects.create(profile=profile, **validated_data)
                PartPurchaseEvent.objects.bulk_create(
                    [PartPurchaseEvent(maintenance_report=maintenance_report, **part_data) for
                     part_data in part_purchase_events_data])
                ServiceProviderEvent.objects.bulk_create(
                    [ServiceProviderEvent(maintenance_report=maintenance_report, **service_event_data)
                     for service_event_data in service_provider_events_data])

            return maintenance_report
        except Exception as e:
            raise serializers.ValidationError(f"Error creating maintenance report: {e}")

    def update(self, instance, validated_data):
        # Extract related data
        part_purchase_events_data = validated_data.pop('part_purchase_events', [])
        service_provider_events_data = validated_data.pop('service_provider_events', [])

        def update_related_objects(manager, related_model, related_data):
            # Fetch existing objects in bulk
            existing_objects = {obj.id: obj for obj in manager.all()}

            # Lists for bulk creation and updates
            new_objects = []
            updated_objects = []

            for item_data in related_data:
                obj_id = item_data.pop('id', None)  # Extract the ID (if any)
                if obj_id and obj_id in existing_objects:
                    # Update existing object
                    obj = existing_objects[obj_id]
                    for attr, value in item_data.items():
                        setattr(obj, attr, value)
                    updated_objects.append(obj)  # Track object for saving later
                else:
                    # Create a new object if ID is missing or invalid
                    new_objects.append(related_model(
                        maintenance_report=instance,
                        **item_data
                    ))

            # Bulk update and create
            if updated_objects:
                related_model.objects.bulk_update(updated_objects, fields=related_data.keys())
            if new_objects:
                related_model.objects.bulk_create(new_objects)

        try:
            with transaction.atomic():
                # Update the MaintenanceReport instance
                for attr, value in validated_data.items():
                    setattr(instance, attr, value)
                instance.save()

                # Update related objects
                update_related_objects(instance.part_purchase_events, PartPurchaseEvent, part_purchase_events_data)
                update_related_objects(instance.service_provider_events, ServiceProviderEvent,
                                       service_provider_events_data)

                return instance
        except PartPurchaseEvent.DoesNotExist as e:
            raise serializers.ValidationError(f"PartPurchaseEvent not found: {e}")
        except ServiceProviderEvent.DoesNotExist as e:
            raise serializers.ValidationError(f"ServiceProviderEvent not found: {e}")
        except Exception as e:
            raise serializers.ValidationError(f"Error updating maintenance report: {e}")
