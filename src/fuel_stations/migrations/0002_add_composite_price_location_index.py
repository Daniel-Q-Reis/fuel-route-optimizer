# Generated manually for composite index optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fuel_stations', '0001_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='fuelstation',
            index=models.Index(
                fields=['retail_price', 'latitude', 'longitude'],
                name='fuel_station_price_location_idx'
            ),
        ),
    ]
