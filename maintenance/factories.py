import factory

from .models import Part, PartsProvider, PartPurchaseEvent, ServiceProvider, ServiceChoices, MaintenanceReport


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


class PartPurchaseEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PartPurchaseEvent

    part = factory.SubFactory(PartFactory)
    provider = factory.SubFactory(ServiceProviderFactory)
    purchase_date = factory.Faker('date')
    cost = factory.Faker('random_int')


class MaintenanceReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MaintenanceReport

    vehicle = factory.SubFactory('vehicles.factories.VehicleFactory')
    service_provider = factory.SubFactory(ServiceProviderFactory)
    start_date = factory.Faker('date')
    end_date = factory.Faker('date')
    cost = factory.Faker('random_int')
    description = factory.Faker('text')
    mileage = factory.Faker('random_int')

    @factory.post_generation
    def parts(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for part in extracted:
                self.parts.add(part)
        else:
            self.parts.add(PartPurchaseEventFactory())
