# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-28 22:03
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('blocks', '0047_auto_20170828_2202'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orphan',
            name='date_time',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
