from rest_framework import status
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from .models import Part, ServiceProvider, PartsProvider, PartPurchaseEvent
from .permissions import IsPartPurchaseEventOwner
from .serializers import PartSerializer, ServiceProviderSerializer, PartsProviderSerializer, PartPurchaseEventSerializer


# Create your views here.

class PartsListView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        parts = Part.objects.all().order_by('name')
        serializer = PartSerializer(parts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = PartSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        raise ValidationError(detail=serializer.errors)


class PartDetailsView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get_object(self, pk):
        try:
            return Part.objects.get(id=pk)
        except Part.DoesNotExist:
            raise NotFound(detail="Part does not exist")

    def get(self, request, pk):
        part = self.get_object(pk)
        serializer = PartSerializer(part)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        part = self.get_object(pk)
        serializer = PartSerializer(part, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        part = self.get_object(pk)
        part.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ServiceProviderListView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        providers = ServiceProvider.objects.all().order_by('name')
        serializer = ServiceProviderSerializer(providers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ServiceProviderSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        raise ValidationError(detail=serializer.errors)


class ServiceProviderDetailsView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get_object(self, pk):
        try:
            return ServiceProvider.objects.get(id=pk)
        except ServiceProvider.DoesNotExist:
            raise NotFound(detail="Service Provider does not exist")

    def get(self, request, pk):
        provider = self.get_object(pk)
        serializer = ServiceProviderSerializer(provider)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        provider = self.get_object(pk)
        serializer = ServiceProviderSerializer(provider, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        provider = self.get_object(pk)
        provider.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PartsProvidersListView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        parts_providers = PartsProvider.objects.all().order_by('name')
        serializer = PartsProviderSerializer(parts_providers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = PartsProviderSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        raise ValidationError(detail=serializer.errors)


class PartsProviderDetailsView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get_object(self, pk):
        try:
            return PartsProvider.objects.get(id=pk)
        except PartsProvider.DoesNotExist:
            raise NotFound(detail="Part Provider does not exist")

    def get(self, request, pk):
        provider = self.get_object(pk)
        serializer = PartsProviderSerializer(provider)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        provider = self.get_object(pk)
        serializer = PartsProviderSerializer(provider, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        provider = self.get_object(pk)
        provider.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PartPurchaseEventsListView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        part_purchase_events = PartPurchaseEvent.objects.filter(profile__user=request.user).order_by('purchase_date')
        paginator = PageNumberPagination()
        paginated_part_purchase_events = paginator.paginate_queryset(part_purchase_events, request)
        serializer = PartPurchaseEventSerializer(paginated_part_purchase_events, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


