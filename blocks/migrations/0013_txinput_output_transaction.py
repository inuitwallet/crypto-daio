# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-11-22 11:24
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('blocks', '0012_auto_20161107_1337'),
    ]

    operations = [
        migrations.AddField(
            model_name='txinput',
            name='output_transaction',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='inout_txs', related_query_name='inout_tx', to='blocks.Transaction'),
            preserve_default=False,
        ),
    ]
