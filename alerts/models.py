from django.db import models

from charts.models import Exchange, Currency


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


class BalanceAlert(Alert):
    exchange = models.ForeignKey(
        Exchange
    )
    currency = models.ForeignKey(
        Currency
    )
