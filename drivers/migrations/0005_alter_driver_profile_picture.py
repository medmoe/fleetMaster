# Generated by Django 5.0.6 on 2024-08-15 21:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drivers', '0004_alter_driver_profile_picture'),
    ]

    operations = [
        migrations.AlterField(
            model_name='driver',
            name='profile_picture',
            field=models.ImageField(null=True, upload_to='profile_pics/'),
        ),
    ]