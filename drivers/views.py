from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import TokenError

from .authentication import DriverRefreshToken, DriverJWTAuthentication
from .models import Driver
from .pagination import CustomPageNumberPagination
from .permissions import IsDriverOwner, IsDriver
from .serializers import DriverSerializer, DriverStartingShiftSerializer


class DriversListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        drivers = Driver.objects.filter(profile__user=request.user).order_by("pk")

        paginator = CustomPageNumberPagination()
        paginated_drivers = paginator.paginate_queryset(drivers, request)
        serializer = DriverSerializer(paginated_drivers, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = DriverSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        raise ValidationError(detail=serializer.errors)


class DriversDetailView(APIView):
    permission_classes = [IsAuthenticated, IsDriverOwner]

    def get_object(self, pk):
        try:
            return Driver.objects.get(id=pk)
        except Driver.DoesNotExist:
            raise NotFound(detail="Driver does not exist.")

    def check_object_permissions(self, request, obj):
        for permission in self.get_permissions():
            if not permission.has_object_permission(request, self, obj):
                self.permission_denied(request, message=getattr(permission, "message", None))

    def get(self, request, pk):
        driver = self.get_object(pk)
        self.check_object_permissions(request, driver)
        serializer = DriverSerializer(driver)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        driver = self.get_object(pk)
        self.check_object_permissions(request, driver)
        serializer = DriverSerializer(driver, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        driver = self.get_object(pk)
        self.check_object_permissions(request, driver)
        driver.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DriverLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny, ]

    def post(self, request):
        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")
        date_of_birth = request.data.get("date_of_birth")
        access_code = request.data.get("access_code")

        if not date_of_birth:
            return Response({"message": "Date of birth is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            parsed_date = parse_date(date_of_birth)
            if not parsed_date:
                return Response({"message": "Date of birth must be in YYYY-MM-DD format."},
                                status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({"message": "Date of birth must be in YYYY-MM-DD format."},
                            status=status.HTTP_400_BAD_REQUEST)

        driver = Driver.objects.filter(
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            access_code=access_code
        ).first()

        if driver:
            try:
                # Use our custom driver tokens instead of user-based tokens
                refresh = DriverRefreshToken.for_driver(driver)
                access = refresh.access_token

                response = Response(data={'driver_id': driver.id})
                response.set_cookie(key='driver_refresh', value=str(refresh),
                                    httponly=True, samesite='None', secure=True)
                response.set_cookie(key='driver_access', value=str(access),
                                    httponly=True, samesite="None", secure=True)
                return response
            except Exception as e:
                return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


class DriverTokenRefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get('driver_refresh')

        if not refresh_token:
            return Response({"message": "Refresh token not found"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            # Parse the refresh token

            token = UntypedToken(refresh_token)

            # Verify it's a driver refresh token
            if token.get('token_type') != 'driver_refresh':
                raise TokenError("Not a driver refresh token")

            # Get the driver
            driver_id = token.get('driver_id')
            driver = Driver.objects.get(pk=driver_id)

            # Create new tokens
            refresh = DriverRefreshToken.for_driver(driver)
            access = refresh.access_token

            # Set the cookies
            response = Response({'success': True})
            response.set_cookie(key='driver_refresh', value=str(refresh),
                                httponly=True, samesite='None', secure=True)
            response.set_cookie(key='driver_access', value=str(access),
                                httponly=True, samesite="None", secure=True)
            return response

        except (TokenError, Driver.DoesNotExist) as e:
            return Response({"message": str(e)}, status=status.HTTP_401_UNAUTHORIZED)


class DriverStartingShiftView(APIView):
    authentication_classes = [DriverJWTAuthentication]
    permission_classes = [IsDriver]

    def post(self, request):

        serializer = DriverStartingShiftSerializer(data={'driver': request.driver.id, **request.data})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
