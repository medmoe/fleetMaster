from django.urls import path

from .views import PartsListView, PartDetailsView, ServiceProviderListView, ServiceProviderDetailsView, PartsProvidersListView, \
    PartsProviderDetailsView, PartPurchaseEventDetailsView, MaintenanceReportListView, MaintenanceReportDetailsView, \
    VehicleMaintenanceReportOverview, GeneralMaintenanceDataView, ServiceProviderEventDetailsView, CSVImportView, FleetWideOverviewView, VehicleReportsListView

urlpatterns = [
    # parts endpoints
    path('parts/', PartsListView.as_view(), name='parts'),
    path('parts/<int:pk>/', PartDetailsView.as_view(), name='part-details'),
    path('parts/upload-parts/', CSVImportView.as_view(), name='upload-parts'),

    # service provider endpoints
    path('service-providers/', ServiceProviderListView.as_view(), name='service-providers'),
    path('service-providers/<int:pk>/', ServiceProviderDetailsView.as_view(), name='service-provider-details'),

    # Parts providers endpoints
    path('parts-providers/', PartsProvidersListView.as_view(), name='parts-providers'),
    path('parts-providers/<int:pk>/', PartsProviderDetailsView.as_view(), name="parts-provider-details"),

    # events endpoints
    path('part-purchase-events/<int:pk>/', PartPurchaseEventDetailsView.as_view(), name='part-purchase-event-details'),
    path('service-provider-events/<int:pk>/', ServiceProviderEventDetailsView.as_view(), name='service-provider-event-details'),

    # reports endpoints
    path('reports/', MaintenanceReportListView.as_view(), name='reports'),
    path('reports/<int:pk>/', MaintenanceReportDetailsView.as_view(), name='reports-details'),
    path('reports/vehicle/<int:pk>/', VehicleReportsListView.as_view(), name='vehicle-reports-list'),

    # statistics endpoints
    path('<int:pk>/overview/', VehicleMaintenanceReportOverview.as_view(), name="overview"),
    path('general-data/', GeneralMaintenanceDataView.as_view(), name="general-data"),
    path('fleet-wide-overview/', FleetWideOverviewView.as_view(), name="fleet-wide-overview"),
]
