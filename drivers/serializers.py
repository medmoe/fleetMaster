from rest_framework import serializers

from .models import Driver


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "license_number",
            "license_expiry_date",
            "date_of_birth",
            "address",
            "city",
            "state",
            "zip_code",
            "country",
            "hire_date",
            "employment_status",
            "emergency_contact_name",
            "emergency_contact_phone",
            "notes",
            "vehicle",
        ]
        read_only_fields = ['profile']

    def create(self, validated_data):
        profile = self.context['request'].user.userprofile
        return Driver.objects.create(profile=profile, **validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

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

            existing_driver_query = Driver.objects.filter(**{field: field_value})
            if self.instance:
                existing_driver_query = existing_driver_query.exclude(pk=self.instance.pk)

            if existing_driver_query:
                raise serializers.ValidationError(f"A driver with this {field.replace('_', ' ')} already exists")

        return data
