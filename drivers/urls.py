from django.urls import path

from .views import DriversListView, DriversDetailView

urlpatterns = [
    path('drivers/', DriversListView.as_view(), name="drivers"),
    path('drivers/<int:pk>', DriversDetailView.as_view(), name="driver-detail"),
]