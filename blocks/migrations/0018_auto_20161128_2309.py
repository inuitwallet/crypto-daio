# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-11-28 23:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blocks', '0017_auto_20161128_2247'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='version',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
