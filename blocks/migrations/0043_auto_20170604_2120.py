# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-06-04 21:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blocks", "0042_auto_20170604_2119"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transaction",
            name="lock_time",
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
    ]
