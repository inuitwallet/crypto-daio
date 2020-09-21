# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-05-08 13:29
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blocks", "0038_auto_20170504_2116"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="txoutput",
            name="addresses",
        ),
        migrations.AddField(
            model_name="txoutput",
            name="address",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="output_addresses",
                related_query_name="output_address",
                to="blocks.Address",
            ),
        ),
    ]
