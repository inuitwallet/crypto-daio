# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-17 22:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('charts', '0021_auto_20170710_1519'),
    ]

    operations = [
        migrations.AddField(
            model_name='currency',
            name='decimal_places',
            field=models.PositiveIntegerField(default=4),
        ),
    ]
