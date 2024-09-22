from django.urls import path

from .views import PartsListView, PartDetailsView, ServiceProviderListView, ServiceProviderDetailsView, PartsProvidersListView, \
    PartsProviderDetailsView

urlpatterns = [
    path('parts/', PartsListView.as_view(), name='parts'),
    path('parts/<int:pk>/', PartDetailsView.as_view(), name='part-details'),
    path('service-providers/', ServiceProviderListView.as_view(), name='service-providers'),
    path('service-providers/<int:pk>/', ServiceProviderDetailsView.as_view(), name='service-provider-details'),
    path('parts-providers/', PartsProvidersListView.as_view(), name='parts-providers'),
    path('parts-providers/<int:pk>/', PartsProviderDetailsView.as_view(), name="parts-provider-details"),
]
