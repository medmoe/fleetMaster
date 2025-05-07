# factories.py
import factory

from vehicles.factories import VehicleFactory  # Adjust import based on actual path
from .models import Driver, EmploymentStatusChoices


class DriverFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Driver
        skip_postgeneration_save = True

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.Faker('email')
    phone_number = factory.Faker('phone_number')
    license_number = factory.Sequence(lambda n: f'LIC{n:05d}')
    license_expiry_date = factory.Faker('date')
    date_of_birth = factory.Faker('date_of_birth')
    address = factory.Faker('address')
    city = factory.Faker('city')
    state = factory.Faker('state_abbr')
    zip_code = factory.Faker('postcode')
    country = factory.Faker('country')
    profile_picture = factory.django.ImageField()
    hire_date = factory.Faker('date_this_decade')
    employment_status = factory.Iterator([choice[0] for choice in EmploymentStatusChoices.choices])
    emergency_contact_name = factory.Faker('name')
    emergency_contact_phone = factory.Faker('phone_number')
    notes = factory.Faker('text', max_nb_chars=200)
