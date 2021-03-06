# Generated by Django 2.2.16 on 2020-09-21 08:57

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blocks", "0063_auto_20191120_0750"),
    ]

    operations = [
        migrations.AlterField(
            model_name="custodianvote",
            name="address",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="blocks.Address",
            ),
        ),
        migrations.AlterField(
            model_name="txoutput",
            name="address",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="outputs",
                related_query_name="output_address",
                to="blocks.Address",
            ),
        ),
    ]
