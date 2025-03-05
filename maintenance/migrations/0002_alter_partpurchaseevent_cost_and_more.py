# Generated by Django 4.2.16 on 2025-03-05 17:23

import core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partpurchaseevent',
            name='cost',
            field=models.IntegerField(validators=[core.validators.validate_positive_integer]),
        ),
        migrations.AlterField(
            model_name='serviceproviderevent',
            name='cost',
            field=models.IntegerField(validators=[core.validators.validate_positive_integer]),
        ),
    ]
