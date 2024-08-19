from rest_framework import serializers

from .models import Driver


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = "__all__"
        read_only_fields = ['profile']

    def create(self, validated_data):
        user = self.context['request'].user
        vehicles = validated_data.pop('vehicles', [])
        driver = Driver.objects.create(profile=user.userprofile, **validated_data)
        driver.vehicles.set(vehicles)
        return driver

