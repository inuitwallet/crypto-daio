# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-04-21 23:16
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blocks", "0020_auto_20170421_2100"),
    ]

    operations = [
        migrations.RenameField(model_name="txoutput", old_name="n", new_name="index",),
        migrations.RemoveField(model_name="transaction", name="is_coin_base",),
        migrations.RemoveField(model_name="transaction", name="is_coin_stake",),
        migrations.RemoveField(model_name="txinput", name="output_transaction",),
        migrations.RemoveField(model_name="txinput", name="tx_id",),
        migrations.RemoveField(model_name="txinput", name="v_out",),
        migrations.RemoveField(model_name="txoutput", name="is_unspent",),
        migrations.AddField(
            model_name="transaction",
            name="index",
            field=models.BigIntegerField(default=-1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="transaction",
            name="time",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="txinput",
            name="previous_output",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="previous_output",
                to="blocks.TxOutput",
            ),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="block",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="transactions",
                related_query_name="transaction",
                to="blocks.Block",
            ),
        ),
        migrations.AlterField(
            model_name="txinput",
            name="transaction",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="inputs",
                related_query_name="input",
                to="blocks.Transaction",
            ),
        ),
        migrations.AlterField(
            model_name="txoutput",
            name="transaction",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="outputs",
                related_query_name="output",
                to="blocks.Transaction",
            ),
        ),
    ]
