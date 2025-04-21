from django.contrib.auth.models import User
from django.core.validators import EmailValidator
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from drivers.models import Driver
from drivers.serializers import DriverSerializer
from vehicles.models import Vehicle
from vehicles.serializers import VehicleSerializer
from .models import UserProfile

# Validation and Authentication error messages
MISSING_USER_DATA_ERROR = "Required user data is missing."
AUTHENTICATION_ERROR = "No active account found with the given credentials."
ACCOUNT_STATUS_ERROR = "Account is not approved yet."
USERNAME_ALREADY_IN_USE_ERROR = 'Username is already in use.'
EMAIL_ALREADY_IN_USE_ERROR = "Email address is already in use."
INVALID_EMAIL_ERROR = "Enter a valid email address."
ACCOUNT_NOT_FOUND_ERROR = "Account does not exist."
IMAGE_UPLOAD_ERROR = "Uploaded file is not a valid image."
UNKNOWN_PROFILE_TYPE = "The profile type provided does not exist."


class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=False)
    email = serializers.CharField(required=True, validators=[EmailValidator(message=INVALID_EMAIL_ERROR)])

    def __init__(self, *args, **kwargs):
        super(UserSerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request', None)
        if request and request.method == "POST":
            self.fields['password'].required = True

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        instance.username = validated_data.get('username', instance.username)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.email = validated_data.get('email', instance.email)
        # Make sure that the password is hashed
        if 'password' in validated_data:
            instance.set_password(validated_data.get('password', instance.password))
        instance.save()
        return instance

    def to_representation(self, instance):
        """ Ensures that the password is not included in the returned data"""

        rep = super().to_representation(instance)
        rep.pop('password', None)
        return rep

    def validate_username(self, value):
        request = self.context['request']
        if User.objects.exclude(pk=request.user.pk).filter(username=value).exists():
            raise ValidationError(detail=USERNAME_ALREADY_IN_USE_ERROR)
        return value

    def validate_email(self, value):
        request = self.context['request']
        if User.objects.exclude(pk=request.user.pk).filter(email=value).exists():
            raise ValidationError(detail=EMAIL_ALREADY_IN_USE_ERROR)
        return value


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = UserProfile
        fields = ["id", "user", "phone", "address", "city", "state", "country", "zip_code"]

    def create(self, validated_data):
        user_data = validated_data.pop('user', None)
        user_serializer = UserSerializer(data=user_data, context=self.context)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        return UserProfile.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        if user_data:
            user_serializer = UserSerializer(instance.user, user_data, context=self.context)
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        account = self._validate_account(attrs)
        data = self._get_tokens_data(attrs)
        serialized_account = UserProfileSerializer(account).data
        data.update(serialized_account)
        data.update(self._get_serialized_data(Driver, DriverSerializer, account))
        data.update(self._get_serialized_data(Vehicle, VehicleSerializer, account))
        return data

    def _get_serialized_data(self, model, serializer, profile):
        queryset = model.objects.filter(profile=profile)
        serializer_data = serializer(queryset, many=True).data
        return {model.__name__.lower() + 's': serializer_data}

    def _get_tokens_data(self, attrs):
        data = super().validate(attrs)
        refresh = self.get_token(self.user)
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)
        return data

    def _validate_account(self, attrs):
        account = UserProfile.objects.filter(user__username=attrs['username']).first()
        if not account:
            raise AuthenticationFailed(detail=AUTHENTICATION_ERROR)
        return account
