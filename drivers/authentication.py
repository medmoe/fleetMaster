import uuid
from datetime import timedelta

from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from rest_framework_simplejwt.tokens import Token
from rest_framework_simplejwt.tokens import UntypedToken

from drivers.models import Driver


class DriverToken(Token):
    token_type = 'driver_access'  # Changed from 'driver' to match what's being set in for_driver
    lifetime = settings.SIMPLE_JWT.get("ACCESS_TOKEN_LIFETIME", timedelta(minutes=120))

    @classmethod
    def for_driver(cls, driver):
        token = cls()
        token['token_type'] = 'driver_access'
        token['driver_id'] = driver.id
        token['first_name'] = driver.first_name
        token['last_name'] = driver.last_name
        token['jti'] = uuid.uuid4().hex

        return token


class DriverRefreshToken(DriverToken):
    """
    Refresh token for driver authentication
    """
    token_type = 'driver_refresh'
    lifetime = settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME')

    @property
    def access_token(self):
        """
        Returns an access token for this refresh token
        """
        access = DriverToken()

        # Copy driver claims to the access token
        access['token_type'] = 'driver_access'
        access['driver_id'] = self['driver_id']
        access['first_name'] = self['first_name']
        access['last_name'] = self['last_name']
        access['jti'] = uuid.uuid4().hex

        return access


class DriverJWTAuthentication(JWTAuthentication):
    """
    Authentication backend that validates driver-specific JWT tokens
    """

    def get_validated_token(self, raw_token):
        """
        Validates a token and returns it
        """
        try:
            # First try normal validation (for admin/manager tokens)
            return super().get_validated_token(raw_token)
        except InvalidToken:
            # If normal validation fails, try driver token validation
            try:
                return self.validate_driver_token(raw_token)
            except Exception as e:
                # Re-raise as InvalidToken to maintain the expected exception type
                raise InvalidToken('Token is not valid') from e

    def validate_driver_token(self, raw_token):
        """
        Validates a driver token
        """
        try:
            # Use UntypedToken to parse and validate the token without type checking
            token = UntypedToken(raw_token)

            # Check if it's a driver token
            if token.get('token_type') != 'driver_access':
                raise InvalidToken('Token is not a valid driver token')

            return token
        except Exception as e:
            raise InvalidToken('Failed to validate driver token') from e

    def get_user(self, validated_token):
        """
        Returns None for driver tokens - we don't want to associate with a User
        """
        # If it's a driver token, return None for the user
        if validated_token.get('token_type') == 'driver_access':
            return None

        # Otherwise use the standard JWT method to get a user
        return super().get_user(validated_token)

    def authenticate(self, request):
        """
        Authenticate the request and return a two-tuple of (user, token).
        For driver tokens, user will be None and driver info will be in the token.
        """
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)

        # For driver tokens, set driver info on the request but return None for user
        if validated_token.get('token_type') == 'driver_access':
            try:
                driver_id = validated_token.get('driver_id')
                driver = Driver.objects.get(pk=driver_id)
                request.driver = driver
                return None, validated_token
            except Driver.DoesNotExist:
                raise AuthenticationFailed('Driver not found')

        # For regular tokens, return the user
        return self.get_user(validated_token), validated_token
