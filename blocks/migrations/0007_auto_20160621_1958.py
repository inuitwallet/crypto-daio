# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blocks", "0006_auto_20160621_1755"),
    ]

    operations = [
        migrations.RemoveField(model_name="block", name="transactions",),
        migrations.RemoveField(model_name="transaction", name="inputs",),
        migrations.RemoveField(model_name="transaction", name="outputs",),
        migrations.AddField(
            model_name="transaction",
            name="block",
            field=models.ForeignKey(
                related_query_name="transaction",
                related_name="transactions",
                default=0,
                to="blocks.Block",
                on_delete=models.SET_NULL,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="txinput",
            name="transaction",
            field=models.ForeignKey(
                related_query_name="input",
                related_name="inputs",
                default=0,
                to="blocks.Transaction",
                on_delete=models.CASCADE,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="txoutput",
            name="transaction",
            field=models.ForeignKey(
                related_query_name="output",
                related_name="outputs",
                default=0,
                to="blocks.Transaction",
                on_delete=models.CASCADE,
            ),
            preserve_default=False,
        ),
    ]
