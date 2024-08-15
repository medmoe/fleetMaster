# Generated by Django 5.0.6 on 2024-08-14 21:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vehicles', '0002_alter_vehicle_vin'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vehicle',
            name='color',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='vehicle',
            name='fuel_type',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='vehicle',
            name='insurance_policy_number',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='vehicle',
            name='make',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='vehicle',
            name='model',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='vehicle',
            name='registration_number',
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name='vehicle',
            name='status',
            field=models.CharField(choices=[('ACTIVE', 'Active'), ('IN_MAINTENANCE', 'In maintenance'), ('OUT_OF_SERVICE', 'Out of service')], default='ACTIVE', max_length=100),
        ),
        migrations.AlterField(
            model_name='vehicle',
            name='type',
            field=models.CharField(choices=[('CAR', 'Car'), ('TRUCK', 'Truck'), ('MOTORCYCLE', 'Motorcycle'), ('VAN', 'Van')], max_length=100),
        ),
        migrations.AlterField(
            model_name='vehicle',
            name='vin',
            field=models.CharField(max_length=100, unique=True),
        ),
    ]