from django.db import connection
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from maintenance.models import Part, ServiceProvider, PartsProvider
from maintenance.queries import COMBINED_YEARLY_DATA_QUERY
from maintenance.serializers import PartSerializer, ServiceProviderSerializer, PartsProviderSerializer
from maintenance.services.fleet_services import FleetHealthService, FleetMaintenanceService, VehicleMaintenanceService
from vehicles.models import Vehicle


class VehicleMaintenanceReportOverview(APIView):
    permission_classes = [IsAuthenticated, ]

    def get_vehicle(self, pk, user):
        try:
            return Vehicle.objects.get(pk=pk, profile__user=user)
        except Vehicle.DoesNotExist:
            raise ValidationError(detail={"Vehicle does not exist!"})

    def get(self, request, pk):
        vehicle = self.get_vehicle(pk, request.user)
        profile = request.user.userprofile.id
        params = [vehicle.id, profile, vehicle.id, profile, vehicle.id, profile, vehicle.id, profile]
        with connection.cursor() as cursor:
            # Pass vehicle_id and profile_id twice (once for each CTE that needs them)
            cursor.execute(COMBINED_YEARLY_DATA_QUERY, params)
            return Response(VehicleMaintenanceService.format_yearly_maintenance_data(cursor.fetchall()), status=status.HTTP_200_OK)


class GeneralMaintenanceDataView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        serialized_parts = PartSerializer(Part.objects.all(), many=True, context={'request': request})
        serialized_service_providers = ServiceProviderSerializer(ServiceProvider.objects.all(), many=True, context={'request': request})
        serialized_parts_providers = PartsProviderSerializer(PartsProvider.objects.all(), many=True, context={'request': request})
        response_data = {"parts": serialized_parts.data, "service_providers": serialized_service_providers.data,
                         "part_providers": serialized_parts_providers.data}
        return Response(response_data, status=status.HTTP_200_OK)


class FleetWideOverviewView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        """
        Handles GET requests for retrieving vehicle-related metrics including core metrics, grouped
        maintenance metrics, and vehicle health metrics. Provides filtered data based on query parameters.

        Parameters:
            request (HttpRequest): The HTTP request object containing query parameters.

        Query Parameters:
            vehicle_type (str, optional): Type of the vehicle to filter metrics.
            start_date (str, optional): Start date in ISO format for filtering metrics over a date range.
            end_date (str, optional): End date in ISO format for filtering metrics over a date range.
            group_by (str, optional): Field to group metrics by, such as 'day', 'week', 'month'.

        Returns:
            Response: A Response object containing either:
                - The combined dictionary of core metrics, vehicle health metrics, and health alerts,
                  if no grouping or date range is provided.
                - The combined dictionary of grouped maintenance metrics, vehicle health, and health alerts,
                  metrics if grouping and/or date range filters are applied.

        Raises:
            None explicitly documented, but potential exceptions may arise due to query parameter
            parsing, database queries, or other runtime issues.
        """
        vehicle_type = request.query_params.get('vehicle_type', None)
        start_date = request.query_params.get('start_date', None)
        end_date = request.query_params.get('end_date', None)
        group_by = request.query_params.get('group_by', None)
        vehicles_count = Vehicle.objects.filter(profile__user=self.request.user).count()
        vehicle_health_metrics, health_alerts = FleetHealthService.get_health_metrics(self.request.user, vehicle_type)

        # Handle request when filters are not provided
        if not group_by and not end_date:
            core_metrics = FleetMaintenanceService.get_core_metrics(self.request.user, vehicle_type)
            return Response(data=core_metrics | {"vehicle_health_metrics": vehicle_health_metrics, "health_alerts": health_alerts}, status=status.HTTP_200_OK)

        grouped_metrics = {"grouped_metrics": FleetMaintenanceService.get_grouped_maintenance_metrics(self.request.user, start_date, end_date, group_by, vehicles_count, vehicle_type)}
        return Response(data=grouped_metrics | {"vehicle_health_metrics": vehicle_health_metrics, "health_alerts": health_alerts}, status=status.HTTP_200_OK)
