import datetime

import factory
from faker import Faker

faker = Faker()

from .models import Part, PartsProvider, PartPurchaseEvent, ServiceProvider, ServiceChoices, MaintenanceReport, \
    MaintenanceChoices, ServiceProviderEvent, VehicleEvent


class PartFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Part

    name = factory.Faker('name')
    description = factory.Faker('text')


class ServiceProviderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceProvider

    name = factory.Faker("name")
    service_type = factory.Iterator([choice[0] for choice in ServiceChoices])
    phone_number = factory.Faker('phone_number')
    address = factory.Faker("address")


class PartsProviderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PartsProvider

    name = factory.Faker("name")
    phone_number = factory.Faker('phone_number')
    address = factory.Faker("address")


class MaintenanceReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MaintenanceReport

    profile = factory.SubFactory("accounts.factories.UserProfileFactory")
    maintenance_type = factory.Iterator([choice[0] for choice in MaintenanceChoices.choices])
    start_date = factory.LazyFunction(faker.date_object)
    end_date = factory.LazyAttribute(lambda obj: faker.date_between(start_date=obj.start_date, end_date=obj.start_date + datetime.timedelta(days=30)))
    description = factory.Faker('text')
    mileage = factory.Faker('random_int')

    @factory.post_generation
    def service_provider_events(self, create, extracted, **kwargs):
        if create and extracted:
            for service_event in extracted:
                ServiceProviderEventFactory(maintenance_report=self, **service_event)

    @factory.post_generation
    def part_purchase_events(self, create, extracted, **kwargs):
        if create and extracted:
            for part_purchase_event in extracted:
                PartPurchaseEventFactory(maintenance_report=self, **part_purchase_event)


class PartPurchaseEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PartPurchaseEvent

    part = factory.SubFactory(PartFactory)
    provider = factory.SubFactory(PartsProviderFactory)
    maintenance_report = factory.SubFactory(MaintenanceReportFactory)
    purchase_date = factory.Faker('date')
    cost = factory.Faker('random_int')


class ServiceProviderEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceProviderEvent

    maintenance_report = factory.SubFactory(MaintenanceReportFactory)
    service_provider = factory.SubFactory(ServiceProviderFactory)
    service_date = factory.Faker('date')
    cost = factory.Faker('random_int')
    description = factory.Faker('text')


class VehicleEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = VehicleEvent

    maintenance_report = factory.SubFactory(MaintenanceReportFactory)
    vehicle = factory.SubFactory("vehicles.factories.VehicleFactory")
