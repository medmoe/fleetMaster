import base64
import hashlib
import hmac
import json
import os

from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework import permissions, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import UserProfileSerializer, CustomTokenObtainPairSerializer


class SignUpView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny, ]

    def post(self, request):
        serializer = UserProfileSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            response = Response(serializer.data, status=status.HTTP_201_CREATED)
            return response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.COOKIES['refresh']
            if refresh_token is None:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            refresh_token = RefreshToken(refresh_token)
            refresh_token.blacklist()
            response = Response(status=status.HTTP_205_RESET_CONTENT)
            response.delete_cookie('refresh')
            response.delete_cookie('access')
            return response
        except Exception as e:
            return Response({'details': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        response.set_cookie(key='refresh', value=response.data['refresh'], httponly=True, samesite='None', secure=True)
        response.set_cookie(key='access', value=response.data['access'], httponly=True, samesite="None", secure=True)
        response.data.pop('refresh')
        response.data.pop('access')
        return response


class TokenVerificationView(TokenRefreshView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request: Request, *args, **kwargs) -> Response:
        access_token = request.COOKIES.get("access", None)
        refresh_token = request.COOKIES.get('refresh', None)
        if access_token:
            try:
                AccessToken(access_token)
                return Response({"message": "User is authenticated"}, status=status.HTTP_200_OK)
            except TokenError:
                if refresh_token:
                    try:
                        refresh = RefreshToken(refresh_token)
                        new_access_token = str(refresh.access_token)
                        response = Response({"message": "Access token refreshed"}, status=status.HTTP_200_OK)
                        response.set_cookie(key="access", value=new_access_token, httponly=True, samesite="Lax")
                        return response
                    except TokenError as e:
                        return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)
                else:
                    return Response({"message": "Access token expired and no refresh token given."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({"message": "No tokens provided"}, status=status.HTTP_400_BAD_REQUEST)


def parse_signed_request(signed_request, secret):
    """
    Parses the signed_request parameter from Facebook.
    Based on: https://developers.facebook.com/docs/games/gamesonfacebook/login#parsingsr
    Returns the decoded payload if the signature is valid, otherwise None.
    """
    try:
        encoded_sig, payload = signed_request.split('.', 1)

        # Decode secretions
        decoded_sig = base64.urlsafe_b64decode(encoded_sig + "==")
        data = json.loads(base64.urlsafe_b64decode(payload + "==").decode('utf-8'))

        # Validate signature
        if data.get('algorithm', '').upper() != 'HMAC-SHA256':
            # Log error: Unknown algorithm
            return None

        expected_sig = hmac.new(secret.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).digest()

        if hmac.compare_digest(decoded_sig, expected_sig):
            return data  # Signature is valid
        else:
            # Log error: Invalid signature
            return None
    except Exception as e:
        # Log error: Failed to parse signed_request
        # print(f"Error parsing signed_request: {e}") # For debugging
        return None


class FacebookDataDeletionView(APIView):
    permission_classes = [AllowAny, ]

    def get(self, request):
        # Respond to potential initial GET check from Facebook
        return Response(status=status.HTTP_200_OK)

    def post(self, request: Request):
        try:
            # 1. Get and Parse Signed Request
            signed_request = request.POST.get('signed_request')
            if not signed_request:
                return Response({'error': 'Missing signed_request'}, status=status.HTTP_400_BAD_REQUEST)

            # Replace settings.FACEBOOK_APP_SECRET with your actual app secret key
            # It's best practice to store this securely (e.g., environment variables via django-decouple)
            app_secret = os.getenv('FB_APP_SECRET')  # Or settings.FACEBOOK_APP_SECRET
            if not app_secret:
                # Log critical error: App Secret not configured
                return Response({'error': 'Server configuration error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            data = parse_signed_request(signed_request, app_secret)

            if not data:
                return Response({'error': 'Invalid signed_request'}, status=status.HTTP_400_BAD_REQUEST)

            facebook_user_id = data.get('user_id')
            if not facebook_user_id:
                return Response({'error': 'User ID not found in signed_request'}, status=status.HTTP_400_BAD_REQUEST)

            # 2. Find and Delete User Data
            # Use SocialAccount model from django-allauth to find the user
            try:
                social_account = SocialAccount.objects.filter(provider='facebook', uid=facebook_user_id).first()
                if social_account:
                    user_to_delete = social_account.user
                    # --- Your Deletion Logic ---
                    # Option 1: Delete the User entirely (cascades to SocialAccount)
                    user_to_delete.delete()
                    # Option 2: Or just delete the SocialAccount link if you want to keep the user record
                    # social_account.delete()
                    # Option 3: Or anonymize user data
                    # ---------------------------

                    # Generate a confirmation code (can just be the user_id or something unique)
                    confirmation_code = f"fb_{facebook_user_id}"
                    status_url = 'https://fleetmasters.net/deletion-confirmation'  # Your status tracking page

                    return Response({'url': status_url, 'confirmation_code': confirmation_code}, status=status.HTTP_200_OK)
                else:
                    # User authenticated via Facebook before, but no matching SocialAccount found now?
                    # Or maybe never existed. Treat as not found.
                    return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

            except SocialAccount.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:  # Catch potential errors during deletion
                # Log the exception e
                return Response({'error': 'Error processing deletion request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


        except Exception as e:
            # Log the exception e
            return Response({'error': f'Unexpected error: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)


class FacebookLogin(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter
