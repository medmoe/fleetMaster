from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from maintenance.models import PartPurchaseEvent, ServiceProviderEvent
from maintenance.serializers import PartPurchaseEventSerializer, ServiceProviderEventSerializer


class PartPurchaseEventDetailsView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get_object(self, pk, user):
        try:
            return PartPurchaseEvent.objects.get(pk=pk, maintenance_report__profile__user=user)
        except PartPurchaseEvent.DoesNotExist:
            raise NotFound(detail="Part purchase even does not exist")

    def put(self, request, pk):
        part_purchase_event = self.get_object(pk, request.user)
        serializer = PartPurchaseEventSerializer(part_purchase_event, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        part_purchase_event = self.get_object(pk, request.user)
        part_purchase_event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ServiceProviderEventDetailsView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get_object(self, pk, user):
        try:
            return ServiceProviderEvent.objects.get(pk=pk, maintenance_report__profile__user=user)
        except ServiceProviderEvent.DoesNotExist:
            raise NotFound(detail="Service provider event does not exist")

    def put(self, request, pk):
        service_provider_event = self.get_object(pk, request.user)
        serializer = ServiceProviderEventSerializer(service_provider_event, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        service_provider_event = self.get_object(pk, request.user)
        with transaction.atomic():
            has_other_events = ServiceProviderEvent.objects.filter(
                maintenance_report_id=service_provider_event.maintenance_report_id,
                maintenance_report__profile__user=request.user
            ).exclude(pk=service_provider_event.pk).exists()
            if has_other_events:
                service_provider_event.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                raise ValidationError(detail={"error": "Cannot delete the only service provider event for this maintenance report."})
