from rest_framework import serializers

from .models import Vehicle


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ["registration_number", "make", "model", "year", "vin", "color", "type", "status", "purchase_date", "last_service_date",
                  "next_service_due", "mileage", "fuel_type", "capacity", "insurance_policy_number", "insurance_expiry_date", "license_expiry_date",
                  "notes", "id"]
        read_only_fields = ['profile']

    def create(self, validated_data):
        profile = self.context['request'].user.userprofile
        return Vehicle.objects.create(profile=profile, **validated_data)
