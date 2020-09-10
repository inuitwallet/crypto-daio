import logging

from caching.base import CachingMixin, CachingManager
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Sum

from blocks.models import Transaction, TxInput, TxOutput
from daio.models import Coin

logger = logging.getLogger(__name__)


class Address(CachingMixin, models.Model):
    address = models.CharField(
        max_length=610,
        unique=True,
        db_index=True,
    )

    # Addresses that are network owned are not counted in the
    # 'Circulating Currency' calculation
    network_owned = models.BooleanField(
        default=False
    )
    coin = models.ForeignKey(
        Coin,
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    objects = CachingManager()

    def __str__(self):
        return self.address

    @property
    def class_type(self):
        return 'Address'

    @property
    def balance(self):
        balance = self.outputs.filter(
            input__isnull=True,
            transaction__block__isnull=False,
            transaction__block__height__isnull=False
        ).aggregate(
            Sum('value')
        )

        return balance['value__sum'] if balance['value__sum'] else 0

    def transactions(self):
        inputs = TxInput.objects.values_list('transaction', flat=True).filter(
            previous_output__address=self,
            transaction__block__isnull=False,
            transaction__block__height__isnull=False
        )
        outputs = TxOutput.objects.values_list('transaction', flat=True).filter(
            address=self,
            transaction__block__isnull=False,
            transaction__block__height__isnull=False
        )
        tx_ids = [tx for tx in inputs] + [tx for tx in outputs]

        return Transaction.objects.filter(
            id__in=tx_ids
        ).order_by(
            '-time'
        )


class WatchAddress(CachingMixin, models.Model):
    address = models.ForeignKey(
        Address,
        related_name='watch_addresses',
        related_query_name='watch_address',
        on_delete=models.CASCADE
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

    objects = CachingManager()
