from django.db import models

from charts.models import Currency, Pair


class Alert(models.Model):
    alert_operator = models.CharField(
        max_length=255,
        choices=[
            ('EQUALS', '='),
            ('LESS_THAN', '<'),
            ('GREATER_THAN', '>'),
        ]
    )
    alert_value = models.DecimalField(
        max_digits=50,
        decimal_places=8
    )
    providers = models.ManyToManyField(
        'Connector'
    )


class BalanceAlert(Alert):
    pair = models.ForeignKey(
        Pair
    )
    currency = models.CharField(
        max_length=10,
        choices=[
            ('BASE', 'Base'),
            ('QUOTE', 'Quote')
        ]
    )
