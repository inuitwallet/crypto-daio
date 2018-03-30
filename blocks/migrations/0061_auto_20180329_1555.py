# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2018-03-29 15:55
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blocks', '0060_auto_20180329_1534'),
    ]

    operations = [
        migrations.AlterField(
            model_name='block',
            name='park_rates',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=list, null=True),
        ),
        migrations.AlterField(
            model_name='block',
            name='vote',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, null=True),
        ),
    ]
