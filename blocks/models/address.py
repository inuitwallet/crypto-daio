import logging

from django.db import models
from django.db.models import Sum, F

logger = logging.getLogger(__name__)


class Address(models.Model):
    address = models.CharField(
        max_length=610,
        unique=True,
        db_index=True,
    )

    def __str__(self):
        return self.address

    @property
    def class_type(self):
        return 'Address'

    @property
    def balance(self):
        outputs = self.outputs.all().aggregate(
            balance=Sum('value')
        )
        return outputs['balance'] / 10000


class WatchAddress(models.Model):
    address = models.ForeignKey(
        Address,
        related_name='watch_addresses',
        related_query_name='watch_address',
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=6
    )
    call_back = models.URLField(
        max_length=610,
    )
    complete = models.BooleanField(
        default=False,
    )
