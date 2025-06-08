# factories.py
import factory

from .models import Driver, EmploymentStatusChoices, DriverStartingShift


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

    @factory.post_generation
    def access_code(self, create, extracted, **kwargs):
        if not create:
            return
        self.access_code = self.generate_access_code()
        self.save()


class DriverStartingShiftFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DriverStartingShift

    driver = None
    date = factory.Faker('date')
    time = factory.Faker('time')
    load = factory.Faker('random_int')
    mileage = factory.Faker('random_int')
    delivery_areas = factory.Faker('random_elements', elements=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'])
    status = factory.Faker('boolean')
