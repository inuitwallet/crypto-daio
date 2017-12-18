import logging

from caching.base import CachingMixin, CachingManager
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Sum

from blocks.models import Transaction
from blocks.models import TxInput

logger = logging.getLogger(__name__)


class Address(CachingMixin, models.Model):
    address = models.CharField(
        max_length=610,
        unique=True,
        db_index=True,
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

        print(balance)

        return balance['value__sum'] / 10000

        # print('unspent = {}'.format(outputs.count()))
        # print('all = {}'.format(self.outputs.all().count()))
        #
        # for output in outputs:
        #     if not output.transaction.block:
        #         continue
        #
        #     if not output.transaction.block.height:
        #         continue
        #
        #     balance += output.display_value
        #
        # # for output in self.outputs.all():
        # #     if not output.transaction.block:
        # #         continue
        # #
        # #     if not output.transaction.block.height:
        # #         continue
        # #
        # #     try:
        # #         if output.input:
        # #             continue
        # #     except TxInput.DoesNotExist:
        # #         balance += output.display_value
        #
        # return balance

    def transactions(self, page=1):
        transactions = Transaction.objects.distinct(
            'tx_id'
        ).filter(
            output__address=self
        ).order_by(
            'tx_id',
            '-time'
        )
        paginator = Paginator(transactions, 50)
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
