from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import UserProfileSerializer, CustomTokenObtainPairSerializer


class SignUpView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny, ]

    def post(self, request):
        serializer = UserProfileSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            account = serializer.save()
            refresh = RefreshToken.for_user(account.user)
            response = Response(serializer.data, status=status.HTTP_201_CREATED)
            response.set_cookie(key='refresh', value=str(refresh), httponly=True, samesite='Lax')
            response.set_cookie(key='access', value=str(refresh.access_token), httponly=True, samesite='Lax')
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
        response.set_cookie(key='refresh', value=response.data['refresh'], httponly=True, samesite='Lax')
        response.set_cookie(key='access', value=response.data['access'], httponly=True, samesite='Lax')
        response.data.pop('refresh')
        response.data.pop('access')
        return response
