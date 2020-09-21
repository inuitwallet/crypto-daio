# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2018-03-09 14:00
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("blocks", "0058_auto_20180209_1450"),
    ]

    operations = [
        migrations.AddField(
            model_name="block",
            name="amount_parked",
            field=django.contrib.postgres.fields.jsonb.JSONField(default={}),
        ),
    ]
