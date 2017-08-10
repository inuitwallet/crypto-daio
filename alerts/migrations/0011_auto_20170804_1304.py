# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-04 13:04
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('charts', '0021_auto_20170710_1519'),
        ('alerts', '0010_alert_period'),
    ]

    operations = [
        migrations.CreateModel(
            name='WatchedAddressBalanceAlert',
            fields=[
                ('alert_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='alerts.Alert')),
                ('address', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='charts.WatchedAddress')),
            ],
            bases=('alerts.alert',),
        ),
        migrations.AddField(
            model_name='alert',
            name='icon',
            field=models.ImageField(blank=True, null=True, upload_to=''),
        ),
        migrations.AddField(
            model_name='alert',
            name='message',
            field=models.TextField(blank=True, default=''),
        ),
    ]