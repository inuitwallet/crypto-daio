# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-05-04 12:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blocks", "0034_auto_20170504_1141"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transaction",
            name="index",
            field=models.BigIntegerField(default=-1),
        ),
    ]
