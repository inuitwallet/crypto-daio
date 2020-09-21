# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-05-24 20:05
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


def set_coins(apps, schema_editor):
    # We can't import the Person model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    Transaction = apps.get_model("blocks", "Transaction")
    Coin = apps.get_model("daio", "Coin")
    for tx in Transaction.objects.all():
        try:
            tx.coin = Coin.objects.get(unit_code=tx.unit)
        except Coin.DoesNotExist:
            continue
        tx.save()


class Migration(migrations.Migration):

    dependencies = [
        ("daio", "0008_coin_vout_n_value"),
        ("blocks", "0039_auto_20170508_1329"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="txinput",
            options={"ordering": ["index"]},
        ),
        migrations.AlterModelOptions(
            name="txoutput",
            options={"ordering": ["index"]},
        ),
        migrations.AddField(
            model_name="transaction",
            name="coin",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="coin",
                related_query_name="coins",
                to="daio.Coin",
            ),
        ),
        migrations.RunPython(set_coins),
    ]
