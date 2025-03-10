from django.core.exceptions import ValidationError


def validate_positive_integer(value):
    if not isinstance(value, int) or value < 0:
        raise ValidationError("Value must be a positive integer.")
