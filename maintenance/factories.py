import datetime
from django.db.models import Sum
import factory
from faker import Faker

faker = Faker()

from .models import Part, PartsProvider, PartPurchaseEvent, ServiceProvider, ServiceChoices, MaintenanceReport, \
    MaintenanceChoices, ServiceProviderEvent


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
        skip_postgeneration_save = True

    maintenance_type = factory.Iterator([choice[0] for choice in MaintenanceChoices.choices])
    start_date = factory.LazyFunction(faker.date_object)
    end_date = factory.LazyAttribute(lambda obj: faker.date_between(start_date=obj.start_date, end_date=obj.start_date + datetime.timedelta(days=30)))
    description = factory.Faker('text')
    mileage = factory.Faker('random_int')
    total_cost = 0 # We will populate this when we create events.

class PartPurchaseEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PartPurchaseEvent
        skip_postgeneration_save = True

    maintenance_report = None
    purchase_date = factory.Faker('date')
    cost = factory.Faker('random_int')

    @factory.post_generation
    def total_cost(self, create, extracted, **kwargs):
        if not create:
            return
        if self.maintenance_report:
            self.maintenance_report.total_cost += self.cost
            self.maintenance_report.save()

class ServiceProviderEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceProviderEvent
        skip_postgeneration_save = True

    maintenance_report = None
    service_date = factory.Faker('date')
    cost = factory.Faker('random_int')
    description = factory.Faker('text')

    @factory.post_generation
    def total_cost(self, create, extracted, **kwargs):
        if not create:
            return
        if self.maintenance_report:
            self.maintenance_report.total_cost += self.cost
            self.maintenance_report.save()
