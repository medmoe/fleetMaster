from django.contrib.auth.models import User
from factory import Faker, SubFactory, LazyAttribute
from factory.django import DjangoModelFactory

from .models import UserProfile


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    first_name = Faker('first_name')
    last_name = Faker('last_name')
    email = Faker('email')
    username = Faker('name')

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop('password', 'password')
        user = model_class.objects.create_user(password=password, *args, **kwargs)
        return user


class UserProfileFactory(DjangoModelFactory):
    class Meta:
        model = UserProfile

    user = SubFactory(UserFactory)
    phone = Faker('phone_number')
    address = Faker('address')
    city = Faker('city')
    state = Faker('state')
    country = Faker('country')
    zip_code = Faker('zipcode')
    is_verified = Faker('boolean')



