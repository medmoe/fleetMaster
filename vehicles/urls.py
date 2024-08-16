from django.urls import path

from .views import VehiclesListView, VehicleDetailView

urlpatterns = [
    path('', VehiclesListView.as_view(), name="vehicles"),
    path('<int:pk>/', VehicleDetailView.as_view(), name="vehicle-detail")
]
