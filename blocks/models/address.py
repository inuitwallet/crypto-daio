import logging
from decimal import Decimal

from django.db import models

from blocks.models import TxOutput

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
        value = Decimal(0.0)
        # get the outputs for the address
        outputs = TxOutput.objects.filter(
            addresses__address=self.address,
        )
        for output in outputs:
            value += Decimal(output.value)
        return value


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
