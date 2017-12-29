import logging

from caching.base import CachingMixin, CachingManager
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Sum

from blocks.models import Transaction
from blocks.models import TxInput
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
        null=True
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

    def transactions(self, page=1):
        transactions = Transaction.objects.filter(
            output__address=self,
            block__isnull=False,
            block__height__isnull=False
        ).order_by(
            '-time'
        )
        paginator = Paginator(transactions, 10)

        return paginator.page(page)


class WatchAddress(CachingMixin, models.Model):
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

    objects = CachingManager()
