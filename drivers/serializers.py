from rest_framework import serializers

from .models import Driver


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = "__all__"
        read_only_fields = ['profile']

    def create(self, validated_data):
        profile = self.context['request'].user.userprofile
        return Driver.objects.create(profile=profile, **validated_data)

    def validate(self, attrs):
        data = super().validate(attrs)
        for field in ['license_expiry_date', 'date_of_birth', 'hire_date']:
            field_value = data.get(field, None)
            if field_value is None:
                raise serializers.ValidationError(f"{field.replace('_', ' ').capitalize()} can't be empty")

        for field in ['license_number', 'phone_number', 'email']:
            field_value = data.get(field, None)
            if field_value is None and field != 'email':
                raise serializers.ValidationError(f"{field.replace('_', ' ').capitalize()} can't be empty")

            if Driver.objects.filter(**{field: field_value}).exists():
                raise serializers.ValidationError(f"A driver with this {field.replace('_', ' ')} already exists")

        return data
