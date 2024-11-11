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


class PartPurchaseEventSerializer(serializers.ModelSerializer):
    provider = serializers.PrimaryKeyRelatedField(queryset=PartsProvider.objects.all())
    part = serializers.PrimaryKeyRelatedField(queryset=Part.objects.all())
    provider_details = PartsProviderSerializer(source='provider', read_only=True)
    part_details = PartSerializer(source='part', read_only=True)

    class Meta:
        model = PartPurchaseEvent
        fields = "__all__"
        read_only_fields = ['profile']

    def create(self, validated_data):
        profile = self.context['request'].user.userprofile
        return PartPurchaseEvent.objects.create(profile=profile, **validated_data)


class MaintenanceReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceReport
        fields = "__all__"
        read_only_fields = ['profile']

    def create(self, validated_data):
        profile = self.context['request'].user.userprofile
        part_purchase_events_data = validated_data.pop('parts')
        maintenance_report = MaintenanceReport.objects.create(profile=profile, **validated_data)
        for part_purchase_event in part_purchase_events_data:
            maintenance_report.parts.add(part_purchase_event)
        return maintenance_report
