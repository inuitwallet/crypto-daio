# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2018-04-17 14:35
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("blocks", "0061_auto_20180329_1555"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="parkrate",
            options={"ordering": ["blocks"]},
        ),
    ]
