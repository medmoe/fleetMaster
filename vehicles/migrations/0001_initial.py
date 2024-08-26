# Generated by Django 5.0.6 on 2024-08-25 21:08

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
                ('registration_number', models.CharField(blank=True, max_length=100)),
                ('make', models.CharField(blank=True, max_length=100)),
                ('model', models.CharField(blank=True, max_length=100)),
                ('year', models.PositiveIntegerField(blank=True)),
                ('vin', models.CharField(blank=True, max_length=100)),
                ('color', models.CharField(blank=True, max_length=100)),
                ('type', models.CharField(choices=[('CAR', 'Car'), ('TRUCK', 'Truck'), ('MOTORCYCLE', 'Motorcycle'), ('VAN', 'Van')], default='TRUCK', max_length=100)),
                ('status', models.CharField(choices=[('ACTIVE', 'Active'), ('IN_MAINTENANCE', 'In maintenance'), ('OUT_OF_SERVICE', 'Out of service')], default='ACTIVE', max_length=100)),
                ('purchase_date', models.DateField(blank=True)),
                ('last_service_date', models.DateField(blank=True)),
                ('next_service_due', models.DateField(blank=True)),
                ('mileage', models.PositiveIntegerField(blank=True)),
                ('fuel_type', models.CharField(blank=True, max_length=100)),
                ('capacity', models.PositiveIntegerField(blank=True)),
                ('insurance_policy_number', models.CharField(blank=True, max_length=100)),
                ('insurance_expiry_date', models.DateField(blank=True)),
                ('license_expiry_date', models.DateField(blank=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.userprofile')),
            ],
        ),
    ]
