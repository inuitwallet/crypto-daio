# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-07-11 08:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blocks', '0043_auto_20170604_2120'),
    ]

    operations = [
        migrations.AddField(
            model_name='txoutput',
            name='park_duration',
            field=models.BigIntegerField(blank=True, null=True),
        ),
    ]