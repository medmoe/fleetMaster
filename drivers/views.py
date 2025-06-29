from datetime import datetime, timedelta

from django.core.cache import cache
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import UntypedToken

from .authentication import DriverRefreshToken, DriverJWTAuthentication
from .models import Driver, DriverStartingShift
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
        ip = self.get_client_ip(request)
        cache_key = f'login_attempts_{ip}'
        attempts = cache.get(cache_key, 0)
        if attempts >= 10:
            return Response({'message': 'Too many login attempts'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

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

        cache.set(cache_key, attempts + 1, timeout=3600)
        return Response({"message": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


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

    def get(self, request):
        shifts = DriverStartingShift.objects.filter(driver=request.driver).order_by("-date")
        paginator = CustomPageNumberPagination()
        paginated_shifts = paginator.paginate_queryset(shifts, request)
        serializer = DriverStartingShiftSerializer(paginated_shifts, many=True)
        return paginator.get_paginated_response(serializer.data)


class DriverStartingShiftDetailView(APIView):
    authentication_classes = [DriverJWTAuthentication]
    permission_classes = [IsDriver]

    def get_object(self, pk):
        try:
            return DriverStartingShift.objects.get(pk=pk)
        except DriverStartingShift.DoesNotExist:
            raise NotFound(detail="Starting shift does not exist.")

    def get(self, request, pk):
        shift = self.get_object(pk)
        serializer = DriverStartingShiftSerializer(shift)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        shift = self.get_object(pk)
        serializer = DriverStartingShiftSerializer(shift, data={'driver': request.driver.id, **request.data})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        shift = self.get_object(pk)
        shift.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DriverAccessCodeView(APIView):
    permission_classes = [IsAuthenticated, IsDriverOwner]
    def get_driver(self, pk):
        try:
            return Driver.objects.get(pk=pk)
        except Driver.DoesNotExist:
            raise NotFound(detail="Driver does not exist.")

    def put(self, request, pk):
        driver = self.get_driver(pk)
        self.check_object_permissions(request, driver)
        driver.access_code = driver.generate_access_code()
        driver.save()
        return Response({'access_code': driver.access_code}, status=status.HTTP_202_ACCEPTED)

class DriverOverdueFormsView(APIView):
    authentication_classes = [DriverJWTAuthentication]
    permission_classes = [IsDriver]
    def get(self, request):
        """
        Returns a list of dates in the last 30 days that don't have any entries in the table.
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=29)

        # Generate all dates in the table for the last 30 days
        all_dates = [(start_date + timedelta(days=i)) for i in range(30)]

        # Get all dates in the table for the last 30 days
        existing_dates = DriverStartingShift.objects.filter(
            driver=request.driver,
            date__gte=start_date,
            date__lte=end_date
        ).values_list('date', flat=True).distinct()

        existing_dates = set(existing_dates)
        missing_dates = [date for date in all_dates if date not in existing_dates]
        return Response({'missing_dates': missing_dates}, status=status.HTTP_200_OK)


