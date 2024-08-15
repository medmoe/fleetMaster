# Generated by Django 5.0.6 on 2024-08-14 12:16

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Vehicle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('registration_number', models.CharField(max_length=20, unique=True)),
                ('make', models.CharField(max_length=50)),
                ('model', models.CharField(max_length=50)),
                ('year', models.PositiveIntegerField()),
                ('vin', models.CharField(max_length=17, unique=True)),
                ('color', models.CharField(max_length=30)),
                ('type', models.CharField(choices=[('CAR', 'Car'), ('TRUCK', 'Truck'), ('MOTORCYCLE', 'Motorcycle'), ('VAN', 'Van')], max_length=20)),
                ('status', models.CharField(choices=[('ACTIVE', 'Active'), ('IN_MAINTENANCE', 'In maintenance'), ('OUT_OF_SERVICE', 'Out of service')], default='ACTIVE', max_length=20)),
                ('purchase_date', models.DateField()),
                ('last_service_date', models.DateField()),
                ('next_service_due', models.DateField()),
                ('mileage', models.PositiveIntegerField()),
                ('fuel_type', models.CharField(max_length=20)),
                ('capacity', models.PositiveIntegerField()),
                ('insurance_policy_number', models.CharField(max_length=50)),
                ('insurance_expiry_date', models.DateField()),
                ('license_expiry_date', models.DateField()),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.userprofile')),
            ],
        ),
    ]