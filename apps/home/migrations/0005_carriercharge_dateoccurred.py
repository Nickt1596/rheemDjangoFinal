# Generated by Django 3.2.6 on 2021-11-26 17:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0004_rheemcharge'),
    ]

    operations = [
        migrations.AddField(
            model_name='carriercharge',
            name='dateOccurred',
            field=models.DateTimeField(auto_now=True),
        ),
    ]