# Generated by Django 4.2.16 on 2025-02-04 17:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        ('vehicles', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MaintenanceReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('maintenance_type', models.CharField(choices=[('PREVENTIVE', 'Preventive'), ('CURATIVE', 'Curative')], default='PREVENTIVE', max_length=50)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('description', models.TextField(blank=True)),
                ('mileage', models.PositiveIntegerField(blank=True, null=True)),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.userprofile')),
            ],
        ),
        migrations.CreateModel(
            name='Part',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='PartsProvider',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('phone_number', models.CharField(max_length=100)),
                ('address', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='ServiceProvider',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('service_type', models.CharField(choices=[('MECHANIC', 'Mechanic'), ('ELECTRICIAN', 'Electrician'), ('CLEANING', 'Cleaning')], default='MECHANIC', max_length=100)),
                ('phone_number', models.CharField(blank=True, max_length=100)),
                ('address', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='VehicleEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('maintenance_report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vehicle_events', to='maintenance.maintenancereport')),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vehicles.vehicle')),
            ],
        ),
        migrations.CreateModel(
            name='ServiceProviderEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_date', models.DateField()),
                ('cost', models.DecimalField(decimal_places=2, max_digits=10)),
                ('receipt', models.ImageField(null=True, upload_to='services/%Y/%m/%d/')),
                ('description', models.TextField(blank=True)),
                ('maintenance_report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_provider_events', to='maintenance.maintenancereport')),
                ('service_provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='maintenance.serviceprovider')),
            ],
        ),
        migrations.CreateModel(
            name='PartPurchaseEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('purchase_date', models.DateField()),
                ('cost', models.DecimalField(decimal_places=2, max_digits=10)),
                ('receipt', models.ImageField(null=True, upload_to='parts/%Y/%m/%d/')),
                ('maintenance_report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='part_purchase_events', to='maintenance.maintenancereport')),
                ('part', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='maintenance.part')),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='maintenance.partsprovider')),
            ],
        ),
    ]
