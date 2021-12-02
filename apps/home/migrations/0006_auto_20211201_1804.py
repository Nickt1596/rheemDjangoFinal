# Generated by Django 3.2.6 on 2021-12-01 23:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0005_carriercharge_dateoccurred'),
    ]

    operations = [
        migrations.AddField(
            model_name='shipment',
            name='destBottomLat',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='shipment',
            name='destLeftLong',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='shipment',
            name='destRightLong',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='shipment',
            name='destTopLat',
            field=models.FloatField(blank=True, null=True),
        ),
    ]