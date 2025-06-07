from django.urls import path

from .views import DriversListView, DriversDetailView, DriverLoginView

urlpatterns = [
    path('', DriversListView.as_view(), name="drivers"),
    path('<int:pk>/', DriversDetailView.as_view(), name="driver-detail"),
    path('login/', DriverLoginView.as_view(), name="driver-login"),
]
