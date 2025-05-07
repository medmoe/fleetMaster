# factories.py
import factory
from factory import fuzzy
from django.utils import timezone
from .models import Vehicle, VehicleTypeChoices, StatusChoices


class VehicleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Vehicle

    registration_number = factory.Sequence(lambda n: f'REG{n:05d}')
    make = factory.Faker('word')
    model = factory.Faker('word')
    year = factory.fuzzy.FuzzyInteger(2000, 2024)
    vin = factory.Sequence(lambda n: f'VIN{n:017d}')
    color = factory.Faker('color_name')
    type = factory.Iterator([choice[0] for choice in VehicleTypeChoices.choices])
    status = factory.Iterator([choice[0] for choice in StatusChoices.choices])
    purchase_date = factory.Faker('date_this_decade')
    last_service_date = factory.Faker('date_this_year')
    next_service_due = factory.LazyAttribute(lambda o: o.last_service_date + timezone.timedelta(days=365))
    mileage = factory.Faker('random_int', min=0, max=200000)
    fuel_type = factory.Faker('word')
    capacity = factory.Faker('random_int', min=1, max=100)
    insurance_policy_number = factory.Sequence(lambda n: f'POLICY{n:05d}')
    insurance_expiry_date = factory.Faker('date_this_year')
    license_expiry_date = factory.Faker('date_this_year')
    notes = factory.Faker('text', max_nb_chars=200)
