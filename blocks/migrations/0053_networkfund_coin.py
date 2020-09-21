# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-12-29 13:38
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("daio", "0011_coin_decimal_places"),
        ("blocks", "0052_auto_20171227_1956"),
    ]

    operations = [
        migrations.AddField(
            model_name="networkfund",
            name="coin",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="daio.Coin",
            ),
        ),
    ]
