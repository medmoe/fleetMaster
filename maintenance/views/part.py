import csv
from io import TextIOWrapper

from rest_framework import status
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from maintenance.models import Part
from maintenance.permissions import IsOwner
from maintenance.serializers import PartSerializer


class PartsListView(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        parts = Part.objects.all().order_by('name')
        serializer = PartSerializer(parts, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = PartSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        raise ValidationError(detail=serializer.errors)


class PartDetailsView(APIView):
    permission_classes = [IsAuthenticated, IsOwner]

    def get_object(self, pk):
        try:
            return Part.objects.get(id=pk)
        except Part.DoesNotExist:
            raise NotFound(detail="Part does not exist")

    def get(self, request, pk):
        part = self.get_object(pk)
        self.check_object_permissions(request, part)
        serializer = PartSerializer(part, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        part = self.get_object(pk)
        self.check_object_permissions(request, part)
        serializer = PartSerializer(part, data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        part = self.get_object(pk)
        self.check_object_permissions(request, part)
        part.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CSVImportView(APIView):
    permission_classes = [IsAuthenticated, ]

    def post(self, request):
        csv_file = request.FILES.get('file')
        if not csv_file or not csv_file.name.endswith('.csv'):
            return Response({"error": "Please upload a CSV file."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decode_file = TextIOWrapper(csv_file.file, encoding='utf-8')
            reader = csv.DictReader(decode_file)

            existing_names = set(Part.objects.all().values_list('name', flat=True))
            parts_to_create = []
            for row in reader:
                if row['name'] and row['description'] and row['name'] not in existing_names:
                    parts_to_create.append(Part(name=row['name'], description=row['description']))

            created_parts = Part.objects.bulk_create(parts_to_create)
            serialized_parts = PartSerializer(created_parts, many=True, context={'request': request})
            return Response(serialized_parts.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
