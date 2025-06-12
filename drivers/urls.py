from django.urls import path

from .views import (DriversListView,
                    DriversDetailView,
                    DriverLoginView,
                    DriverStartingShiftView,
                    DriverStartingShiftDetailView,
                    DriverAccessCodeView
                    )

urlpatterns = [
    path('', DriversListView.as_view(), name="drivers"),
    path('<int:pk>/', DriversDetailView.as_view(), name="driver-detail"),
    path('login/', DriverLoginView.as_view(), name="driver-login"),
    path('starting-shift/', DriverStartingShiftView.as_view(), name="starting-shift"),
    path('starting-shift/<int:pk>/', DriverStartingShiftDetailView.as_view(), name="starting-shift-detail"),
    path('<int:pk>/access-code/', DriverAccessCodeView.as_view(), name='access-code'),
]
