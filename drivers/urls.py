from django.urls import path

from .views import DriversListView, DriversDetailView

urlpatterns = [
    path('drivers/', DriversListView.as_view(), name="drivers"),
    path('driver-detail/', DriversDetailView.as_view(), name="driver-detail"),
]