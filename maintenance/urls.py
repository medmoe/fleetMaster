from django.urls import path

from .views import PartsListView, PartDetailsView, ServiceProviderListView, ServiceProviderDetailsView, PartsProvidersListView, \
    PartsProviderDetailsView, PartPurchaseEventDetailsView, MaintenanceReportListView, MaintenanceReportDetailsView, \
    MaintenanceReportOverviewView, GeneralMaintenanceDataView, ServiceProviderEventDetailsView

urlpatterns = [
    path('parts/', PartsListView.as_view(), name='parts'),
    path('parts/<int:pk>/', PartDetailsView.as_view(), name='part-details'),
    path('service-providers/', ServiceProviderListView.as_view(), name='service-providers'),
    path('service-providers/<int:pk>/', ServiceProviderDetailsView.as_view(), name='service-provider-details'),
    path('parts-providers/', PartsProvidersListView.as_view(), name='parts-providers'),
    path('parts-providers/<int:pk>/', PartsProviderDetailsView.as_view(), name="parts-provider-details"),
    path('part-purchase-events/<int:pk>/', PartPurchaseEventDetailsView.as_view(), name='part-purchase-event-details'),
    path('service-provider-events/<int:pk>/', ServiceProviderEventDetailsView.as_view(), name='service-provider-event-details'),
    path('reports/', MaintenanceReportListView.as_view(), name='reports'),
    path('reports/<int:pk>/', MaintenanceReportDetailsView.as_view(), name='reports-details'),
    path('overview/', MaintenanceReportOverviewView.as_view(), name="overview"),
    path('general-data/', GeneralMaintenanceDataView.as_view(), name="general-data"),
]
