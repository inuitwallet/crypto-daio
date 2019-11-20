import datetime

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models

from charts.models import Pair, WatchedAddress


class Notification(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()
    date_time = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    def __str__(self):
        return '{} {}'.format(self.date_time, self.content_object)


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
    connectors = models.ManyToManyField(
        'Connector'
    )
    period = models.DurationField(default=datetime.timedelta(minutes=20))
    message = models.TextField(blank=True, default='')
    icon = models.ImageField(
        height_field=None,
        width_field=None,
        blank=True,
        null=True
    )
    notifications = GenericRelation(
        Notification,
        related_query_name='alerts'
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

    def __str__(self):
        return '{} {} @ {}'.format(
            self.alert_operator,
            self.alert_value,
            self.pair
        )


class WatchedAddressBalanceAlert(Alert):
    address = models.ForeignKey(
        WatchedAddress
    )

    def __str__(self):
        return '{} {} @ {}'.format(
            self.alert_operator,
            self.alert_value,
            self.address
        )
