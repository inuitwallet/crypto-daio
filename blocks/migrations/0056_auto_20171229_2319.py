# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-12-29 23:19
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blocks", "0055_auto_20171229_2018"),
    ]

    operations = [
        migrations.AlterField(
            model_name="feesvote",
            name="fee",
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name="parkrate",
            name="rate",
            field=models.FloatField(default=0),
        ),
    ]
