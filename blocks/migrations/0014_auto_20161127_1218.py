# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-11-27 12:18
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blocks", "0013_txinput_output_transaction"),
    ]

    operations = [
        migrations.AlterField(
            model_name="txinput",
            name="output_transaction",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="inout_txs",
                related_query_name="inout_tx",
                to="blocks.Transaction",
            ),
        ),
    ]
