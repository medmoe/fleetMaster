# Generated by Django 5.0.6 on 2024-08-14 20:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drivers', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='driver',
            name='city',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='driver',
            name='country',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='driver',
            name='emergency_contact_name',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='driver',
            name='emergency_contact_phone',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='driver',
            name='employment_status',
            field=models.CharField(choices=[('ACTIVE', 'Active'), ('INACTIVE', 'Inactive'), ('ON_LEAVE', 'On leave')], default='ACTIVE', max_length=100),
        ),
        migrations.AlterField(
            model_name='driver',
            name='first_name',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='driver',
            name='last_name',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='driver',
            name='phone_number',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='driver',
            name='state',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='driver',
            name='zip_code',
            field=models.CharField(max_length=100),
        ),
    ]
