# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2018-01-10 19:32
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("daio", "0011_coin_decimal_places"),
        ("blocks", "0056_auto_20171229_2319"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExchangeBalance",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("exchange", models.CharField(blank=True, max_length=255, null=True)),
                ("api_url", models.URLField(blank=True, max_length=255, null=True)),
                ("api_token", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "coin",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="daio.Coin",
                    ),
                ),
            ],
        ),
    ]
